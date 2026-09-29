"""Align overall metrics of several runs and report comparability warnings."""

from typing import Any

from tsllm.runs.store import RunStore, job_name


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def compare_runs(store: RunStore, run_ids: list[str]) -> dict[str, Any]:
    """Return run columns, one row per (split, overall metric), and warnings."""
    columns: list[dict[str, Any]] = []
    metrics: dict[str, dict[str, Any]] = {}
    for run_id in run_ids:
        job, status = store.read_job(run_id), store.read_status(run_id)
        run = job.run
        columns.append(
            {
                "run_id": run_id,
                "name": job_name(job),
                "dataset": job.dataset.id,
                "task": run.task.type if run else None,
                "backbone": run.backbone.name if run else None,
                "mode": run.mode if run else None,
                "state": status.state,
                "context_length": run.task.context_length if run else None,
                "horizon": getattr(run.task, "horizon", None) if run else None,
            }
        )
        metrics[run_id] = store.read_metrics(run_id) or {}

    rows: dict[tuple[str, str], dict[str, float | None]] = {}
    for run_id, payload in metrics.items():
        for split, result in payload.get("splits", {}).items():
            for name, value in (result.get("overall") or {}).items():
                if value is None or (
                    isinstance(value, (int, float)) and not isinstance(value, bool)
                ):
                    rows.setdefault((split, name), {})[run_id] = value
    for values in rows.values():
        for run_id in run_ids:
            values.setdefault(run_id, None)

    warnings = [
        _warning("RUN_NOT_SUCCEEDED", f"run '{c['run_id']}' state is '{c['state']}'")
        for c in columns
        if c["state"] != "succeeded"
    ]
    for key, code in [
        ("dataset", "DATASET_MISMATCH"),
        ("task", "TASK_MISMATCH"),
        ("context_length", "CONTEXT_LENGTH_MISMATCH"),
        ("horizon", "HORIZON_MISMATCH"),
    ]:
        values = {c[key] for c in columns if c[key] is not None}
        if len(values) > 1:
            warnings.append(_warning(code, f"runs have different {key} values"))
    splits = sorted({split for payload in metrics.values() for split in payload.get("splits", {})})
    for split in splits:
        hashes = {
            payload["splits"][split].get("origin_set_hash")
            for payload in metrics.values()
            if split in payload.get("splits", {})
        }
        if len(hashes) > 1:
            warnings.append(
                _warning(
                    "ORIGIN_SET_MISMATCH", f"runs have different origin sets in split '{split}'"
                )
            )
    return {
        "columns": columns,
        "rows": [
            {"split": split, "metric": name, "values": values}
            for (split, name), values in rows.items()
        ],
        "warnings": warnings,
    }
