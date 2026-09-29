"""Future-event classification from frozen backbone representations."""

from time import perf_counter
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl
from numpy.typing import NDArray

from tsllm.backbones import Backbone
from tsllm.config.run import ClassifyTaskConfig, EvalSplit, HeadConfig
from tsllm.data.labels import future_event_labels, resolve_threshold
from tsllm.data.types import PreparedFrame
from tsllm.data.windows import (
    build_eval_manifest,
    build_train_manifest,
    context_batch,
    origin_set_hash,
)
from tsllm.evaluation.metrics import choose_threshold, classification_metrics
from tsllm.evaluation.resources import Timer, latency_percentiles, peak_vram_mb
from tsllm.reporting import Reporter
from tsllm.tasks.context import TaskContext
from tsllm.tasks.registry import register_task
from tsllm.tasks.validation import TaskConfigError

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline


def _embed(
    backbone: Backbone,
    prepared: PreparedFrame,
    rows: NDArray[np.int64],
    length: int,
    batch_size: int,
    reporter: Reporter,
    latencies: list[float],
) -> NDArray[np.float32]:
    parts = []
    for start in range(0, len(rows), batch_size):
        batch = context_batch(prepared, rows[start : start + batch_size], length)
        began = perf_counter()
        parts.append(backbone.embed(batch))
        latencies.append((perf_counter() - began) * 1000)
        reporter.progress(min(start + batch_size, len(rows)), len(rows))
    return np.concatenate(parts)


def _fit_head(
    cfg: HeadConfig, x: NDArray[np.float32], y: NDArray[np.int8], seed: int
) -> "Pipeline":
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.utils.class_weight import compute_sample_weight

    head = (
        LogisticRegression(C=cfg.C, max_iter=cfg.max_iter)
        if cfg.type == "logistic"
        else MLPClassifier(
            hidden_layer_sizes=tuple(cfg.hidden_layer_sizes),
            max_iter=cfg.max_iter,
            random_state=seed,
        )
    )
    # The scaler is fitted on training representations only.
    pipeline = Pipeline([("scale", StandardScaler()), ("head", head)])
    weights = compute_sample_weight(cfg.class_weight, y) if cfg.class_weight else None
    pipeline.fit(x, y, head__sample_weight=weights)
    return pipeline


@register_task("classify")
def run_classify(ctx: TaskContext) -> dict[str, Any]:
    import joblib

    run, prepared, reporter = ctx.run, ctx.prepared, ctx.reporter
    task = run.task
    assert isinstance(task, ClassifyTaskConfig)
    length, rule = task.context_length, task.label
    threshold = resolve_threshold(prepared, rule)

    reporter.stage("load")
    backbone, load_seconds = ctx.load_backbone()

    manifests = {
        "train": build_train_manifest(prepared, length, rule.window, task.train_origin_stride)
    }
    if manifests["train"].height > task.max_train_origins:
        picks = np.linspace(0, manifests["train"].height - 1, task.max_train_origins)
        manifests["train"] = manifests["train"][picks.astype(np.int64)]
    eval_splits: list[EvalSplit] = ["val", *[s for s in task.eval_splits if s != "val"]]
    for split in eval_splits:
        manifests[split] = build_eval_manifest(
            prepared, split, length, rule.window, task.eval_origin_stride, task.max_eval_origins
        )
    for name, manifest in manifests.items():
        if manifest.is_empty():
            raise TaskConfigError(
                f"split '{name}' has no origins for context {length} and window {rule.window}"
            )

    latencies: list[float] = []
    labels, scores = {}, {}
    reporter.stage("finetune")
    with Timer() as timer:
        rows = manifests["train"]["origin_row"].to_numpy()
        x = _embed(backbone, prepared, rows, length, task.embed_batch_size, reporter, latencies)
        labels["train"] = future_event_labels(prepared, rows, rule, threshold)
        if np.unique(labels["train"]).size < 2:
            raise TaskConfigError("training labels contain one class")
        head = _fit_head(task.head, x, labels["train"], run.seed)
    train_seconds = timer.seconds
    (ctx.run_dir / "adapter").mkdir(exist_ok=True)
    joblib.dump(head, ctx.run_dir / "adapter" / "head.joblib")

    for split in [s for s in manifests if s != "train"]:
        reporter.stage(f"evaluate:{split}")
        rows = manifests[split]["origin_row"].to_numpy()
        x = _embed(backbone, prepared, rows, length, task.embed_batch_size, reporter, latencies)
        labels[split] = future_event_labels(prepared, rows, rule, threshold)
        scores[split] = head.predict_proba(x)[:, 1]

    warnings: list[str] = []
    decision = choose_threshold(labels["val"], scores["val"])
    if decision is None:
        decision = 0.5
        warnings.append("validation split has one class; decision threshold is 0.5")

    ctx.write_json(
        "label_info.json",
        {
            "rule": rule.model_dump(mode="json"),
            "threshold": threshold,
            "splits": {
                name: {"n": len(values), "positive_rate": float(values.mean())}
                for name, values in labels.items()
            },
        },
    )

    splits: dict[str, Any] = {}
    (ctx.run_dir / "predictions").mkdir(exist_ok=True)
    for split in task.eval_splits:
        overall, curves, split_warnings = classification_metrics(
            labels[split], scores[split], decision
        )
        warnings.extend(f"split '{split}': {warning}" for warning in split_warnings)
        splits[split] = {
            "overall": overall,
            "curves": curves,
            "n_origins": len(labels[split]),
            "origin_set_hash": origin_set_hash(manifests[split]),
        }
        pl.DataFrame(
            {
                "origin_time": manifests[split]["origin_time"],
                "label": pl.Series(labels[split], dtype=pl.Int8),
                "score": pl.Series(scores[split], dtype=pl.Float32),
            }
        ).write_parquet(ctx.run_dir / "predictions" / f"{split}.parquet")

    for warning in warnings:
        reporter.log(warning, level="warning")
    p50, p95 = latency_percentiles(latencies)
    return {
        "task": "classify",
        "splits": splits,
        "resources": {
            "load_seconds": load_seconds,
            "train_seconds": train_seconds,
            "peak_vram_mb": peak_vram_mb() if run.backbone.device == "cuda" else None,
            "latency_ms_p50": p50,
            "latency_ms_p95": p95,
            "latency_batch_size": task.embed_batch_size,
        },
        "warnings": warnings,
    }
