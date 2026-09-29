import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import polars as pl
import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import load_json
from tsllm.config.run import JobSpec, RunConfig
from tsllm.runs.store import RunStore
from tsllm.runs.worker import main

COMMON_FILES = ["config.yaml", "status.json", "events.jsonl", "env.json"]
EXPERIMENT_FILES = [*COMMON_FILES, "fit_stats.json", "metrics.json"]
RESOURCE_KEYS = {
    "load_seconds",
    "train_seconds",
    "peak_vram_mb",
    "latency_ms_p50",
    "latency_ms_p95",
    "latency_batch_size",
}


def run_job(cfg: DatasetConfig, run: RunConfig | None) -> tuple[RunStore, str, int]:
    store = RunStore(Path("runs"))
    kind = "ingest" if run is None else "experiment"
    run_id = store.create(JobSpec(kind=kind, dataset=cfg, run=run))
    return store, run_id, main(store.path(run_id))


def events(run_dir: Path) -> list[dict]:
    lines = (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


@pytest.mark.parametrize(("backbone", "mode"), [("persistence", "zero_shot"), ("ridge", "full")])
def test_forecast_run_writes_contract_files(
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
    backbone: str,
    mode: str,
) -> None:
    store, run_id, code = run_job(ingested_config, forecast_run(backbone, mode))
    run_dir = store.path(run_id)
    assert code == 0, events(run_dir)[-1]
    status = store.read_status(run_id)
    assert status.state == "succeeded" and status.finished_at is not None
    for name in [*EXPERIMENT_FILES, "predictions/val.parquet", "predictions/test.parquet"]:
        assert (run_dir / name).is_file(), name
    assert (run_dir / "adapter").is_dir() == (mode != "zero_shot")

    metrics = load_json(run_dir / "metrics.json")
    assert metrics["task"] == "forecast" and set(metrics["splits"]) == {"val", "test"}
    assert set(metrics["resources"]) == RESOURCE_KEYS
    assert (metrics["resources"]["train_seconds"] is None) == (mode == "zero_shot")
    assert metrics["resources"]["peak_vram_mb"] is None
    test = metrics["splits"]["test"]
    assert set(test["overall"]) == {
        "mae_norm_macro",
        "rmse_norm_macro",
        "pinball",
        "coverage_80",
        "width_80",
    }
    assert test["overall"]["mae_norm_macro"] > 0
    assert set(test["per_lead"]) == {"1", "10"}
    assert set(test["per_channel"]) == {"late", "operating", "signal"}
    assert test["excluded_channels"] == []
    assert test["n_origins"] > 0 and len(test["origin_set_hash"]) == 12

    predictions = pl.read_parquet(run_dir / "predictions" / "test.parquet")
    assert predictions.columns == ["origin_time", "channel", "lead", "y_true", "y_pred"]
    assert predictions.height == test["n_origins"] * 3 * 10
    stages = [e["name"] for e in events(run_dir) if e["kind"] == "stage"]
    expected = ["load", *(["finetune"] if mode != "zero_shot" else []), "evaluate:val"]
    assert stages == [*expected, "evaluate:test", "done"]
    env = load_json(run_dir / "env.json")
    assert env["backbone"]["name"] == backbone and "scikit-learn" in env["packages"]
    fit_stats = load_json(run_dir / "fit_stats.json")
    assert set(fit_stats["channels"]) == {"late", "operating", "signal"}


def test_classify_run_writes_contract_files(
    ingested_config: DatasetConfig, classify_run: Callable[..., RunConfig]
) -> None:
    store, run_id, code = run_job(ingested_config, classify_run())
    run_dir = store.path(run_id)
    assert code == 0, events(run_dir)[-1]
    for name in [*EXPERIMENT_FILES, "label_info.json", "adapter/head.joblib"]:
        assert (run_dir / name).is_file(), name
    metrics = load_json(run_dir / "metrics.json")
    assert metrics["task"] == "classify" and set(metrics["resources"]) == RESOURCE_KEYS
    for split in ("val", "test"):
        result = metrics["splits"][split]
        assert set(result["overall"]) == {
            "auroc",
            "auprc",
            "f1",
            "brier",
            "positive_rate",
            "confusion",
            "threshold",
        }
        assert result["overall"]["auroc"] is not None
        assert set(result["curves"]) == {"roc", "pr"}
        predictions = pl.read_parquet(run_dir / "predictions" / f"{split}.parquet")
        assert predictions.columns == ["origin_time", "label", "score"]
        assert predictions.height == result["n_origins"]
    assert metrics["splits"]["val"]["overall"]["threshold"] == pytest.approx(
        metrics["splits"]["test"]["overall"]["threshold"]
    )
    label_info = load_json(run_dir / "label_info.json")
    assert set(label_info["splits"]) == {"train", "val", "test"}
    assert 0 < label_info["splits"]["train"]["positive_rate"] < 1


def test_ingest_job(synthetic_config: DatasetConfig, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store, run_id, code = run_job(synthetic_config, None)
    run_dir = store.path(run_id)
    assert code == 0 and store.read_status(run_id).state == "succeeded"
    assert sorted(p.name for p in run_dir.iterdir()) == sorted(COMMON_FILES)
    assert load_json(run_dir / "env.json")["backbone"] is None


def test_failure_records_traceback_and_summary(
    synthetic_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    store, run_id, code = run_job(synthetic_config, forecast_run("persistence", "zero_shot"))
    status = store.read_status(run_id)
    assert code == 1 and status.state == "failed"
    assert status.error is not None and status.error.startswith("DatasetNotIngested: ")
    assert "\n" not in status.error
    errors = [e for e in events(store.path(run_id)) if e["kind"] == "log"]
    assert errors[-1]["level"] == "error" and "Traceback" in errors[-1]["msg"]
    assert not (store.path(run_id) / "metrics.json").exists()


def test_worker_module_entry_point(
    ingested_config: DatasetConfig, forecast_run: Callable[..., RunConfig]
) -> None:
    store = RunStore(Path("runs"))
    run = forecast_run("persistence", "zero_shot")
    run_id = store.create(JobSpec(kind="experiment", dataset=ingested_config, run=run))
    result = subprocess.run(
        [sys.executable, "-m", "tsllm.runs.worker", str(store.path(run_id))],
        capture_output=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    status = store.read_status(run_id)
    assert status.state == "succeeded" and status.pid is not None
