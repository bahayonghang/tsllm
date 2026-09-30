"""Run comparison with comparability warnings."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import dump_json
from tsllm.config.run import JobSpec, RunConfig
from tsllm.runs.store import RunState, RunStore
from tsllm.service.models import CompareWarningOut
from tsllm.service.settings import Settings


def _in_state(store: RunStore, job: JobSpec, state: RunState) -> str:
    run_id = store.create(job)
    store.transition(run_id, "running", writer="worker")
    store.transition(run_id, state, writer="worker")
    return run_id


def _finished(
    store: RunStore, job: JobSpec, state: RunState, test_hash: str, mae: float | None
) -> str:
    run_id = _in_state(store, job, state)
    splits = {
        "val": {"overall": {"mae_norm_macro": 1.0}, "origin_set_hash": "v"},
        "test": {
            "overall": {"mae_norm_macro": mae, "coverage_80": 0.8},
            "origin_set_hash": test_hash,
        },
    }
    dump_json({"task": "forecast", "splits": splits}, store.path(run_id) / "metrics.json")
    return run_id


def test_compare_rows_and_warnings(
    client: TestClient,
    service_settings: Settings,
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
) -> None:
    store = RunStore(service_settings.runs_dir)

    def job(**task: Any) -> JobSpec:
        run = forecast_run("persistence", "zero_shot", **task)
        return JobSpec(kind="experiment", dataset=ingested_config, run=run)

    a = _finished(store, job(), "succeeded", "h1", 0.5)
    b = _finished(store, job(), "succeeded", "h1", None)
    same = client.get("/api/compare", params={"run_ids": f"{a},{b},{a}"}).json()
    assert [c["run_id"] for c in same["columns"]] == [a, b]
    assert same["warnings"] == []
    rows = {(r["split"], r["metric"]): r["values"] for r in same["rows"]}
    assert rows[("test", "mae_norm_macro")] == {a: 0.5, b: None}
    assert rows[("val", "mae_norm_macro")] == {a: 1.0, b: 1.0}

    c = _finished(store, job(horizon=5, eval_leads=[1]), "failed", "h2", 0.7)
    other = client.get("/api/compare", params={"run_ids": f"{a},{c}"}).json()
    codes = {w["code"] for w in other["warnings"]}
    assert codes == {"RUN_NOT_SUCCEEDED", "HORIZON_MISMATCH", "ORIGIN_SET_MISMATCH"}

    missing = client.get("/api/compare", params={"run_ids": f"{a},nope"})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "RUN_NOT_FOUND"
    empty = client.get("/api/compare", params={"run_ids": ""})
    assert empty.status_code == 422


def _snapshot(settings: Settings) -> dict[str, tuple[bytes, int]]:
    return {
        f"{root.name}/{path.relative_to(root).as_posix()}": (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for root in (settings.runs_dir, settings.configs_dir, settings.cache_dir)
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(
    "selection",
    [(1,), (1, 2), (0, 1), (1, 0), (0, 1, 2), (2, 0, 1, 2, 0, 1)],
    ids=["single-ingest", "all-ingest", "mixed", "reverse", "multi-ingest", "duplicates"],
)
def test_ingest_warnings_preserve_results_and_files(
    client: TestClient,
    service_settings: Settings,
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
    selection: tuple[int, ...],
) -> None:
    store = RunStore(service_settings.runs_dir)
    experiment = JobSpec(
        kind="experiment",
        dataset=ingested_config,
        run=forecast_run("persistence", "zero_shot"),
    )
    ingest = JobSpec(kind="ingest", dataset=ingested_config)
    ids = [
        _finished(store, experiment, "succeeded", "h1", 0.5),
        _in_state(store, ingest, "succeeded"),
        _in_state(store, ingest, "succeeded"),
    ]
    assert all(not (store.path(run_id) / "metrics.json").exists() for run_id in ids[1:])
    selected = list(dict.fromkeys(ids[index] for index in selection))
    before = _snapshot(service_settings)
    response = client.get(
        "/api/compare", params={"run_ids": ",".join(ids[index] for index in selection)}
    )
    assert response.status_code == 200
    result = response.json()
    assert [column["run_id"] for column in result["columns"]] == selected
    assert result["warnings"] == [
        {
            "code": "NON_EXPERIMENT_RUN",
            "message": f"run '{run_id}' is an ingest job and has no experiment metrics",
            "run_id": run_id,
            "split": None,
        }
        for run_id in selected
        if run_id in ids[1:]
    ]
    if ids[0] in selected:
        assert result["rows"] == [
            {
                "split": split,
                "metric": metric,
                "values": {run_id: value if run_id == ids[0] else None for run_id in selected},
            }
            for split, metric, value in [
                ("val", "mae_norm_macro", 1.0),
                ("test", "mae_norm_macro", 0.5),
                ("test", "coverage_80", 0.8),
            ]
        ]
    else:
        assert result["rows"] == []
    for column in result["columns"]:
        if column["run_id"] in ids[1:]:
            assert column["state"] == "succeeded"
            assert all(
                column[key] is None
                for key in ("task", "backbone", "mode", "context_length", "horizon")
            )
    assert _snapshot(service_settings) == before


def test_ingest_warning_follows_existing_warnings_and_preserves_messages(
    client: TestClient,
    service_settings: Settings,
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
    classify_run: Callable[..., RunConfig],
) -> None:
    store = RunStore(service_settings.runs_dir)
    other_dataset = ingested_config.model_copy(update={"id": "synthetic-other"})
    first = JobSpec(
        kind="experiment",
        dataset=ingested_config,
        run=forecast_run("persistence", "zero_shot"),
    )
    different = JobSpec(
        kind="experiment",
        dataset=other_dataset,
        run=forecast_run("persistence", "zero_shot", horizon=5, eval_leads=[1]).model_copy(
            update={"dataset": other_dataset.id}
        ),
    )
    a = _finished(store, first, "succeeded", "h1", 0.5)
    b = _finished(store, different, "failed", "h2", 0.7)
    metrics = store.read_metrics(b)
    assert metrics is not None
    metrics["splits"]["val"]["origin_set_hash"] = "v2"
    dump_json(metrics, store.path(b) / "metrics.json")
    c = _in_state(
        store, JobSpec(kind="experiment", dataset=ingested_config, run=classify_run()), "failed"
    )
    d = _in_state(store, JobSpec(kind="ingest", dataset=ingested_config), "failed")
    before = _snapshot(service_settings)
    response = client.get("/api/compare", params={"run_ids": f"{a},{d},{b},{c}"})
    assert response.status_code == 200
    assert response.json()["warnings"] == [
        {
            "code": code,
            "message": message,
            "run_id": run_id,
            "split": split,
        }
        for code, message, run_id, split in [
            ("RUN_NOT_SUCCEEDED", f"run '{d}' state is 'failed'", d, None),
            ("RUN_NOT_SUCCEEDED", f"run '{b}' state is 'failed'", b, None),
            ("RUN_NOT_SUCCEEDED", f"run '{c}' state is 'failed'", c, None),
            ("DATASET_MISMATCH", "runs have different dataset values", None, None),
            ("TASK_MISMATCH", "runs have different task values", None, None),
            ("CONTEXT_LENGTH_MISMATCH", "runs have different context_length values", None, None),
            ("HORIZON_MISMATCH", "runs have different horizon values", None, None),
            (
                "ORIGIN_SET_MISMATCH",
                "runs have different origin sets in split 'test'",
                None,
                "test",
            ),
            ("ORIGIN_SET_MISMATCH", "runs have different origin sets in split 'val'", None, "val"),
            (
                "NON_EXPERIMENT_RUN",
                f"run '{d}' is an ingest job and has no experiment metrics",
                d,
                None,
            ),
        ]
    ]
    assert _snapshot(service_settings) == before


@pytest.mark.parametrize("run_ids", [None, "", ",", "r1,", "../r1", "r1 r2"])
def test_compare_rejects_invalid_ids(client: TestClient, run_ids: str | None) -> None:
    response = client.get("/api/compare", params={} if run_ids is None else {"run_ids": run_ids})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_experiment_without_metrics_is_not_classified_by_name(
    client: TestClient,
    service_settings: Settings,
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
) -> None:
    store = RunStore(service_settings.runs_dir)
    run = forecast_run("persistence", "zero_shot").model_copy(update={"name": "ingest-synthetic"})
    job = JobSpec(kind="experiment", dataset=ingested_config, run=run)
    run_id = _in_state(store, job, "succeeded")
    assert not (store.path(run_id) / "metrics.json").exists()
    result = client.get("/api/compare", params={"run_ids": run_id})
    assert result.status_code == 200
    assert result.json()["warnings"] == []
    assert result.json()["rows"] == []


def test_warning_context_is_optional_and_codes_stay_open() -> None:
    warning = CompareWarningOut(code="FUTURE_WARNING", message="Future warning details")
    assert warning.run_id is None and warning.split is None
    schema = CompareWarningOut.model_json_schema()
    assert schema["required"] == ["code", "message"]
    for field in ("run_id", "split"):
        assert schema["properties"][field]["default"] is None
        assert schema["properties"][field]["description"]
