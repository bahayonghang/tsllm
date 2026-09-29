"""Command line entry point."""

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Annotated

import typer

from tsllm.config.dataset import SPLIT_NAMES
from tsllm.data.cache import config_hash, is_fresh, read_cache
from tsllm.data.prepare import ingest_dataset
from tsllm.data.registry import list_datasets, load_dataset
from tsllm.errors import TsllmError
from tsllm.reporting import PrintReporter

app = typer.Typer(
    help="Run time-series experiments.", no_args_is_help=True, pretty_exceptions_show_locals=False
)
data_app = typer.Typer(
    help="List, ingest, and profile configured datasets.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
app.add_typer(data_app, name="data")


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
