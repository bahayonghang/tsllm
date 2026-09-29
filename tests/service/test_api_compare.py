"""Run comparison with comparability warnings."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import dump_json
from tsllm.config.run import JobSpec, RunConfig
from tsllm.runs.store import RunStore
from tsllm.service.settings import Settings


def _finished(store: RunStore, job: JobSpec, state: str, test_hash: str, mae: float | None) -> str:
    run_id = store.create(job)
    store.transition(run_id, "running", writer="worker")
    store.transition(run_id, state, writer="worker")  # type: ignore[arg-type]
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
