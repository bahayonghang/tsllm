"""Build deterministic synthetic files without running an ingestion or worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import dump_json, dump_yaml
from tsllm.config.run import JobSpec, RunConfig
from tsllm.data.cache import is_fresh, write_cache
from tsllm.data.types import PreparedFrame
from tsllm.runs.compare import compare_runs
from tsllm.runs.store import TERMINAL_STATES, RunStatus, RunStore

CHANNELS = ["synthetic_a", "synthetic_b"]
IDS = {
    "forecast": "20260101-000001-synthetic-forecast-0001",
    "different": "20260101-000002-synthetic-different-0002",
    "classify": "20260101-000003-synthetic-classify-0003",
    "ingest_failed": "20260101-000004-synthetic-ingest-0004",
    "ingest_succeeded": "20260101-000005-synthetic-ingest-0005",
}
WARNING_CODES = sorted(
    [
        "RUN_NOT_SUCCEEDED",
        "DATASET_MISMATCH",
        "TASK_MISMATCH",
        "CONTEXT_LENGTH_MISMATCH",
        "HORIZON_MISMATCH",
        "ORIGIN_SET_MISMATCH",
        "NON_EXPERIMENT_RUN",
    ]
)


def snapshot(root: Path) -> dict[str, dict[str, int | str]]:
    return {
        path.relative_to(root).as_posix(): {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        for area in ("configs", "cache", "runs", "source")
        for path in sorted((root / area).rglob("*"))
        if path.is_file()
    }


def make_dataset(root: Path, dataset_id: str, offset: float) -> DatasetConfig:
    times = [datetime(2026, 1, 1) + timedelta(minutes=index) for index in range(240)]
    values = [round(offset + math.sin(index / 9) + index / 100, 5) for index in range(240)]
    source = root / "source" / f"{dataset_id}.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "time,synthetic_a,synthetic_b\n"
        + "".join(
            f"{stamp.isoformat()},{value},{round(value * 0.5 + 0.3, 5)}\n"
            for stamp, value in zip(times, values, strict=True)
        ),
        encoding="utf-8",
        newline="\n",
    )
    os.utime(source, ns=(1767225600000000000, 1767225600000000000))
    cfg = DatasetConfig.model_validate(
        {
            "id": dataset_id,
            "source": {"path": str(source), "time_column": "time"},
            "native_freq": "1min",
            "freq": "1min",
            "channels": [
                {"name": name, "role": "target", "unit": "synthetic-unit"} for name in CHANNELS
            ],
            "segments": {"max_gap": "2min", "min_length": "10min"},
        }
    )
    eligible = [not 110 <= index < 120 for index in range(240)]
    frame = pl.DataFrame(
        {
            "time": times,
            "synthetic_a": [
                value if flag else None for value, flag in zip(values, eligible, strict=True)
            ],
            "synthetic_b": [
                round(value * 0.5 + 0.3, 5) if flag else None
                for value, flag in zip(values, eligible, strict=True)
            ],
            "observed": eligible,
            "eligible": eligible,
            "segment_id": [0 if index < 110 else -1 if index < 120 else 1 for index in range(240)],
            "split": [
                "fit" if index < 171 else "val" if index < 194 else "cal" if index < 217 else "test"
                for index in range(240)
            ],
        },
        schema_overrides={
            "time": pl.Datetime("us"),
            "synthetic_a": pl.Float32,
            "synthetic_b": pl.Float32,
            "segment_id": pl.Int32,
            "split": pl.Categorical,
        },
    )
    prepared = PreparedFrame(
        frame,
        CHANNELS,
        cfg.freq,
        {
            "split_boundaries": dict(
                zip(
                    ("fit", "val", "cal", "test"),
                    (times[index].isoformat() for index in (0, 171, 194, 217)),
                    strict=True,
                )
            )
        },
    )
    (root / "configs" / "datasets").mkdir(parents=True, exist_ok=True)
    dump_yaml(cfg, root / "configs" / "datasets" / f"{dataset_id}.yaml")
    write_cache(cfg, prepared, root / "cache" / "datasets")
    assert is_fresh(cfg, root / "cache" / "datasets")
    return cfg


def forecast_metrics(tag: str, missing: bool = False) -> dict:
    return {
        "task": "forecast",
        "splits": {
            split: {
                "overall": {
                    "mae_norm_macro": None if missing else 0.12,
                    "rmse_norm_macro": 0.18,
                    "pinball": 0.03,
                    "coverage_80": 0.8,
                    "width_80": 0.4,
                },
                "per_channel": {name: {"mae": 0.12, "rmse": 0.18} for name in CHANNELS},
                "per_lead": {str(lead): {"mae_norm_macro": 0.1 + lead / 100} for lead in (1, 3, 6)},
                "n_origins": 2,
                "origin_set_hash": f"{tag}-{split}",
            }
            for split in ("val", "test")
        },
        "resources": {
            "load_seconds": 0.01,
            "peak_vram_mb": 0,
            "latency_ms_p50": 0.4,
            "latency_ms_p95": 0.6,
            "train_seconds": 0,
        },
    }


def classify_metrics() -> dict:
    return {
        "task": "classify",
        "splits": {
            split: {
                "overall": {
                    "auroc": 0.86,
                    "auprc": 0.81,
                    "f1": 0.8,
                    "brier": 0.15,
                    "positive_rate": 0.4,
                    "confusion": [[12, 2], [2, 8]],
                    "threshold": 0.5,
                },
                "curves": {
                    "roc": [[0, 0], [0.1, 0.65], [0.3, 0.9], [1, 1]],
                    "pr": [[0, 1], [0.5, 0.9], [0.8, 0.75], [1, 0.4]],
                },
                "n_origins": 24,
                "origin_set_hash": f"classify-{split}",
            }
            for split in ("val", "test")
        },
        "resources": {"load_seconds": 0.01, "peak_vram_mb": 0, "train_seconds": 0.1},
    }


def write_job(root: Path, key: str, job: JobSpec, state: str, metrics: dict | None) -> None:
    directory = root / "runs" / IDS[key]
    directory.mkdir(parents=True)
    dump_yaml(job, directory / "config.yaml")
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    status = RunStatus.model_validate(
        {
            "state": state,
            "created_at": stamp,
            "started_at": stamp,
            "finished_at": stamp + timedelta(seconds=1),
            "pid": None,
            "error": "Synthetic failure fixture" if state == "failed" else None,
        }
    )
    dump_json(status.model_dump(mode="json"), directory / "status.json")
    dump_json(
        {"fixture": True, "note": "Synthetic fixture; no worker executed"}, directory / "env.json"
    )
    (directory / "events.jsonl").write_text(
        json.dumps(
            {
                "ts": stamp.isoformat(),
                "kind": "log",
                "level": "info",
                "message": "Synthetic terminal fixture; no worker executed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if metrics is not None:
        dump_json(metrics, directory / "metrics.json")


def create(root: Path) -> dict:
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("Fixture destination must be empty; existing files are preserved")
    root.mkdir(parents=True, exist_ok=True)
    alpha = make_dataset(root, "synthetic-alpha", 0)
    beta = make_dataset(root, "synthetic-beta", 0.5)
    base = RunConfig.model_validate(
        {
            "name": "Synthetic forecast",
            "dataset": alpha.id,
            "task": {
                "type": "forecast",
                "context_length": 12,
                "horizon": 6,
                "eval_leads": [1, 3, 6],
            },
            "backbone": {"name": "persistence", "device": "cpu", "dtype": "fp32"},
            "mode": "zero_shot",
            "notes": "Synthetic measurement fixture only",
        }
    )
    different = RunConfig.model_validate(
        base.model_dump(mode="json")
        | {
            "name": "Synthetic different failed",
            "dataset": beta.id,
            "task": {
                "type": "forecast",
                "context_length": 16,
                "horizon": 8,
                "eval_leads": [1, 3, 6],
            },
        }
    )
    classify = RunConfig.model_validate(
        {
            "name": "Synthetic classification",
            "dataset": alpha.id,
            "task": {
                "type": "classify",
                "context_length": 10,
                "label": {
                    "type": "future_event",
                    "channel": CHANNELS[0],
                    "op": "gt",
                    "threshold": {"value": 1.5},
                    "window": 3,
                    "min_duration": 1,
                },
            },
            "backbone": {"name": "features", "device": "cpu", "dtype": "fp32"},
            "mode": "head",
            "notes": "Synthetic measurement fixture only",
        }
    )
    for key, dataset, run, state, metrics in (
        ("forecast", alpha, base, "succeeded", forecast_metrics("base")),
        ("different", beta, different, "failed", forecast_metrics("different", True)),
        ("classify", alpha, classify, "succeeded", classify_metrics()),
        ("ingest_failed", alpha, None, "failed", None),
        ("ingest_succeeded", beta, None, "succeeded", None),
    ):
        write_job(
            root,
            key,
            JobSpec(kind="experiment" if run else "ingest", dataset=dataset, run=run),
            state,
            metrics,
        )
    prediction_dir = root / "runs" / IDS["forecast"] / "predictions"
    prediction_dir.mkdir()
    for split, origins in (("val", (172, 180)), ("test", (217, 225))):
        rows = []
        for origin in origins:
            for channel in CHANNELS:
                for lead in range(1, 7):
                    value = round(math.sin((origin + lead) / 9) + (origin + lead) / 100, 5)
                    if channel == CHANNELS[1]:
                        value = round(value * 0.5 + 0.3, 5)
                    rows.append(
                        {
                            "origin_time": datetime(2026, 1, 1) + timedelta(minutes=origin),
                            "channel": channel,
                            "lead": lead,
                            "y_true": value,
                            "y_pred": value + 0.08,
                            "q_0.1": value - 0.12,
                            "q_0.9": value + 0.28,
                        }
                    )
        pl.DataFrame(rows).write_parquet(prediction_dir / f"{split}.parquet")
    (root / "configs" / "runs").mkdir(parents=True)
    dump_yaml(base, root / "configs" / "runs" / "synthetic-preview.yaml")
    store = RunStore(root / "runs")
    summaries = store.list()
    assert len(summaries) == 5 and all(item.state in TERMINAL_STATES for item in summaries)
    comparison = compare_runs(store, list(IDS.values()))
    assert sorted({item["code"] for item in comparison["warnings"]}) == WARNING_CODES
    manifest = {
        "schema_version": 1,
        "synthetic_only": True,
        "fixture_roots": {name: name for name in ("runs", "cache", "configs", "source")},
        "ids": IDS,
        "datasets": [alpha.id, beta.id],
        "template": "synthetic-preview",
        "warning_codes": WARNING_CODES,
        "warning_count": len(comparison["warnings"]),
        "row_count": 240,
        "segment_count": 2,
        "files": snapshot(root),
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.verify:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        actual = snapshot(root)
        assert actual == manifest["files"], "Fixture files or mtimes changed"
        output = {"unchanged": True, "files": len(actual), "ids": manifest["ids"]}
    else:
        output = create(root)
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {key: value for key, value in output.items() if key != "files"}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
