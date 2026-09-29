"""Worker entry point: python -m tsllm.runs.worker <run_dir>."""

import logging
import os
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tsllm.backbones import Backbone, list_backbones
from tsllm.config.io import dump_json
from tsllm.config.run import JobSpec
from tsllm.data.cache import read_cache
from tsllm.data.prepare import ingest_dataset
from tsllm.data.stats import compute_fit_stats
from tsllm.reporting import Reporter
from tsllm.runs.env import environment_snapshot
from tsllm.runs.reporter import FileReporter
from tsllm.runs.seeding import seed_everything
from tsllm.runs.store import RunStore
from tsllm.tasks import TaskContext, get_task
from tsllm.tasks.validation import validate_job


def _write_env(run_dir: Path, job: JobSpec, backbone: Backbone | None = None) -> None:
    fields: dict[str, Any] = {}
    if backbone is not None:
        info = {entry.name: entry for entry in list_backbones()}[backbone.name]
        resolved = backbone.resolved_checkpoint
        fields = {
            "license": info.license,
            "resolved_checkpoint": str(resolved.path) if resolved else None,
            "resolved_revision": resolved.revision if resolved else None,
        }
    dump_json(environment_snapshot(job, **fields), run_dir / "env.json")


def _run_experiment(run_dir: Path, job: JobSpec, reporter: Reporter) -> dict[str, Any]:
    assert job.run is not None
    validate_job(job)
    prepared = read_cache(job.dataset)
    fit_stats = compute_fit_stats(prepared)
    dump_json(asdict(fit_stats), run_dir / "fit_stats.json")
    ctx = TaskContext(run_dir, job, job.run, prepared, fit_stats, reporter)
    try:
        return get_task(job.run.task.type)(ctx)
    finally:
        # Some adapters resolve the checkpoint at first use, so record it after the task.
        if ctx.backbone is not None:
            _write_env(run_dir, job, ctx.backbone)


def main(run_dir: Path, *, mirror: Reporter | None = None) -> int:
    """Execute one queued job. Every failure after the running transition is recorded."""
    store, run_id = RunStore(run_dir.parent), run_dir.name
    store.transition(run_id, "running", writer="worker", pid=os.getpid())
    reporter = FileReporter(run_dir / "events.jsonl", mirror=mirror)
    try:
        job = store.read_job(run_id)
        seed_everything(job.run.seed if job.run is not None else 0)
        _write_env(run_dir, job)
        if job.kind == "ingest":
            ingest_dataset(job.dataset, reporter)
        else:
            dump_json(_run_experiment(run_dir, job, reporter), run_dir / "metrics.json")
            reporter.stage("done")
        store.transition(run_id, "succeeded", writer="worker")
        return 0
    except Exception as exc:
        reporter.log(traceback.format_exc(), level="error")
        summary = " ".join(f"{type(exc).__name__}: {exc}".split())
        store.transition(run_id, "failed", writer="worker", error=summary)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for name in ("transformers", "urllib3", "huggingface_hub"):
        logging.getLogger(name).setLevel(logging.WARNING)
    sys.exit(main(Path(sys.argv[1])))
