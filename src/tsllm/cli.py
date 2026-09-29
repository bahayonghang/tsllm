"""Command line entry point."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from pydantic import ValidationError

from tsllm.config.dataset import SPLIT_NAMES
from tsllm.config.io import load_yaml
from tsllm.config.run import JobSpec, RunConfig
from tsllm.config.schema import run_config_schema
from tsllm.data.cache import config_hash, is_fresh, read_cache
from tsllm.data.prepare import ingest_dataset
from tsllm.data.registry import list_datasets, load_dataset
from tsllm.errors import TsllmError
from tsllm.reporting import PrintReporter
from tsllm.runs.store import RunStore
from tsllm.runs.worker import main as worker_main
from tsllm.tasks.validation import validate_job

app = typer.Typer(
    help="Run time-series experiments.", no_args_is_help=True, pretty_exceptions_show_locals=False
)
data_app = typer.Typer(
    help="List, ingest, and profile configured datasets.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
runs_app = typer.Typer(
    help="List and inspect run directories.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
api_app = typer.Typer(
    help="Export the HTTP API description.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
app.add_typer(data_app, name="data")
app.add_typer(runs_app, name="runs")
app.add_typer(api_app, name="api")


@app.callback()
def main() -> None:
    """Configure datasets and run offline experiments."""


@contextmanager
def _domain_errors() -> Iterator[None]:
    try:
        yield
    except TsllmError as error:
        typer.echo(f"{error.code}: {error}", err=True)
        raise typer.Exit(code=1) from None


@data_app.command("list")
def data_list() -> None:
    """Show registered datasets and current cache status."""
    with _domain_errors():
        datasets = list_datasets()
        if not datasets:
            typer.echo("No datasets registered.")
            return
        typer.echo("id\tsource\tcache\thash")
        for cfg in datasets:
            status = "ready" if is_fresh(cfg) else "missing_or_stale"
            typer.echo(f"{cfg.id}\t{cfg.source.path}\t{status}\t{config_hash(cfg)}")


@data_app.command("ingest")
def data_ingest(
    dataset_id: Annotated[str, typer.Argument(help="Registered dataset id.")],
    force: Annotated[bool, typer.Option("--force", help="Rebuild a current cache.")] = False,
) -> None:
    """Prepare a dataset and write its Parquet cache and profile."""
    with _domain_errors():
        cfg = load_dataset(dataset_id)
        start = perf_counter()
        prepared = ingest_dataset(cfg, PrintReporter(), force=force)
        meta = prepared.meta
        typer.echo(
            f"dataset={cfg.id} rows={meta['rows']} eligible_points={meta['eligible_points']} "
            f"segments={meta['segment_count']} elapsed_seconds={perf_counter() - start:.3f}"
        )


@data_app.command("profile")
def data_profile(
    dataset_id: Annotated[str, typer.Argument(help="Registered dataset id.")],
) -> None:
    """Show counts, split boundaries, and channel null rates from a current cache."""
    with _domain_errors():
        cfg = load_dataset(dataset_id)
        meta = read_cache(cfg).meta
        typer.echo(f"dataset={cfg.id} freq={meta['freq']}")
        typer.echo(
            f"rows={meta['rows']} observed_points={meta['observed_points']} "
            f"eligible_points={meta['eligible_points']} segments={meta['segment_count']}"
        )
        for split in SPLIT_NAMES:
            counts = meta["splits"][split]
            typer.echo(
                f"{split}: rows={counts['rows']} eligible_points={counts['eligible_points']}"
            )
        for split, boundary in meta["split_boundaries"].items():
            typer.echo(f"{split}_start={boundary}")
        for name in meta["channel_names"]:
            typer.echo(f"{name}: null_rate={meta['channels'][name]['null_rate']:.6f}")


def _store() -> RunStore:
    return RunStore(Path("runs"))


def _execute(store: RunStore, job: JobSpec) -> str:
    """Create a run directory as the service writer, then execute it as the worker."""
    run_id = store.create(job)
    typer.echo(f"run_id={run_id}")
    code = worker_main(store.path(run_id), mirror=PrintReporter())
    status = store.read_status(run_id)
    typer.echo(f"state={status.state}")
    if code != 0:
        typer.echo(f"error: {status.error}", err=True)
        raise typer.Exit(code=1)
    return run_id


@app.command("run")
def run(
    config: Annotated[Path, typer.Argument(help="RunConfig YAML file.")],
    ingest: Annotated[
        bool, typer.Option("--ingest", help="Ingest the dataset first when its cache is stale.")
    ] = False,
) -> None:
    """Execute one run in the foreground and write its run directory."""
    with _domain_errors():
        try:
            cfg = load_yaml(RunConfig, config)
        except ValidationError as error:
            typer.echo(f"VALIDATION_ERROR: {error}", err=True)
            raise typer.Exit(code=1) from None
        dataset = load_dataset(cfg.dataset)
        store = _store()
        if ingest:
            _execute(store, JobSpec(kind="ingest", dataset=dataset))
        job = JobSpec(kind="experiment", dataset=dataset, run=cfg)
        validate_job(job)
        run_id = _execute(store, job)
        metrics = store.read_metrics(run_id) or {}
        for split, result in metrics.get("splits", {}).items():
            values = " ".join(
                f"{name}={value:.6g}"
                for name, value in result["overall"].items()
                if isinstance(value, float)
            )
            typer.echo(f"{split}: {values}")


@runs_app.command("list")
def runs_list() -> None:
    """Show runs, newest first."""
    with _domain_errors():
        summaries = _store().list()
        if not summaries:
            typer.echo("No runs.")
            return
        typer.echo("run_id	state	kind	dataset	task	backbone	mode	metric")
        for s in summaries:
            metric = "" if s.primary_metric is None else f"{s.primary_metric}={s.primary_value:.6g}"
            typer.echo(
                f"{s.run_id}	{s.state}	{s.kind}	{s.dataset}	{s.task or ''}	"
                f"{s.backbone or ''}	{s.mode or ''}	{metric}"
            )


@runs_app.command("show")
def runs_show(run_id: Annotated[str, typer.Argument(help="Run id.")]) -> None:
    """Show the status, configuration summary, and metrics of one run."""
    with _domain_errors():
        store = _store()
        status = store.read_status(run_id)
        job = store.read_job(run_id)
        typer.echo(json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2))
        if job.run is not None:
            typer.echo(
                f"name={job.run.name} dataset={job.dataset.id} task={job.run.task.type} "
                f"backbone={job.run.backbone.name} mode={job.run.mode}"
            )
        metrics = store.read_metrics(run_id)
        if metrics is not None:
            summary = {
                "splits": {
                    split: {key: result[key] for key in ("overall", "n_origins", "origin_set_hash")}
                    for split, result in metrics["splits"].items()
                },
                "resources": metrics["resources"],
                "warnings": metrics.get("warnings", []),
            }
            typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))


@app.command("schema")
def schema() -> None:
    """Print the RunConfig JSON Schema and backbone Options schemas."""
    typer.echo(json.dumps(run_config_schema(), ensure_ascii=False, indent=2))


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port.")] = 8000,
) -> None:
    """Start the HTTP API and the job queue."""
    import uvicorn

    from tsllm.service.app import create_app

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    uvicorn.run(create_app(), host=host, port=port)


@api_app.command("openapi")
def api_openapi(
    out: Annotated[Path, typer.Option("--out", help="Output JSON file.")],
) -> None:
    """Write the OpenAPI document of the HTTP API."""
    from tsllm.service.app import create_app

    document = create_app().openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    typer.echo(f"paths={len(document['paths'])} out={out}")
