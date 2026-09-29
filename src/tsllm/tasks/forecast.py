"""Zero-shot and fine-tuned forecasting evaluated on fixed chronological origins."""

from time import perf_counter
from typing import Any

import numpy as np
import polars as pl
from numpy.typing import NDArray

from tsllm.config.run import ForecastTaskConfig
from tsllm.data.windows import (
    build_eval_manifest,
    context_batch,
    origin_set_hash,
    segment_set,
    targets,
)
from tsllm.evaluation.metrics import forecast_metrics
from tsllm.evaluation.resources import Timer, latency_percentiles, peak_vram_mb
from tsllm.tasks.context import TaskContext
from tsllm.tasks.registry import register_task
from tsllm.tasks.validation import TaskConfigError


def _predictions(
    times: NDArray[np.datetime64],
    channels: list[str],
    y_true: NDArray[np.float32],
    mean: NDArray[np.float32],
    quantiles: NDArray[np.float32] | None,
    levels: list[float] | None,
) -> pl.DataFrame:
    n, c, h = mean.shape
    columns: dict[str, pl.Series] = {
        "origin_time": pl.Series(np.repeat(times, c * h), dtype=pl.Datetime("us")),
        "channel": pl.Series(np.tile(np.repeat(np.asarray(channels), h), n), dtype=pl.String),
        "lead": pl.Series(np.tile(np.arange(1, h + 1), n * c), dtype=pl.Int32),
        "y_true": pl.Series(y_true.reshape(-1), dtype=pl.Float32, nan_to_null=True),
        "y_pred": pl.Series(mean.reshape(-1), dtype=pl.Float32, nan_to_null=True),
    }
    if quantiles is not None and levels is not None:
        for k, level in enumerate(levels):
            columns[f"q_{level:g}"] = pl.Series(
                quantiles[..., k].reshape(-1), dtype=pl.Float32, nan_to_null=True
            )
    return pl.DataFrame(columns)


@register_task("forecast")
def run_forecast(ctx: TaskContext) -> dict[str, Any]:
    run, prepared, reporter = ctx.run, ctx.prepared, ctx.reporter
    task = run.task
    assert isinstance(task, ForecastTaskConfig)
    length, horizon = task.context_length, task.horizon
    channels = list(prepared.channels)

    reporter.stage("load")
    backbone, load_seconds = ctx.load_backbone()
    train_seconds = None
    if run.mode != "zero_shot":
        reporter.stage("finetune")
        train = segment_set(prepared, "fit", min_rows=length + horizon)
        val = segment_set(prepared, "val", min_rows=length + horizon)
        with Timer() as timer:
            backbone.finetune(
                train,
                val if val.arrays else None,
                run.finetune,
                length,
                horizon,
                reporter,
                mode=run.mode,
            )
        train_seconds = timer.seconds
        backbone.save_adapter(ctx.run_dir / "adapter")

    fit_std = [ctx.fit_stats.channels[name].std for name in channels]
    latencies: list[float] = []
    splits: dict[str, Any] = {}
    warnings: list[str] = []
    (ctx.run_dir / "predictions").mkdir(exist_ok=True)
    for split in task.eval_splits:
        reporter.stage(f"evaluate:{split}")
        manifest = build_eval_manifest(
            prepared, split, length, horizon, task.eval_origin_stride, task.max_eval_origins
        )
        if manifest.is_empty():
            raise TaskConfigError(
                f"split '{split}' has no evaluation origins for context {length} "
                f"and horizon {horizon}"
            )
        rows = manifest["origin_row"].to_numpy()
        means, quantiles, levels = [], [], None
        for start in range(0, len(rows), task.eval_batch_size):
            batch = context_batch(prepared, rows[start : start + task.eval_batch_size], length)
            began = perf_counter()
            output = backbone.forecast(batch, horizon)
            latencies.append((perf_counter() - began) * 1000)
            means.append(output.mean)
            if output.quantiles is not None:
                quantiles.append(output.quantiles)
                levels = output.quantile_levels
            reporter.progress(min(start + task.eval_batch_size, len(rows)), len(rows))
        mean = np.concatenate(means)
        stacked = np.concatenate(quantiles) if quantiles else None
        y_true, mask = targets(prepared, rows, horizon)
        result = forecast_metrics(
            y_true, mask, mean, stacked, levels, fit_std, task.eval_leads, channels
        )
        result["n_origins"] = len(rows)
        result["origin_set_hash"] = origin_set_hash(manifest)
        splits[split] = result
        if result["n_missing_predictions"]:
            warnings.append(
                f"split '{split}' has {result['n_missing_predictions']} "
                "non-finite predictions at observed targets"
            )
        _predictions(
            manifest["origin_time"].to_numpy(), channels, y_true, mean, stacked, levels
        ).write_parquet(ctx.run_dir / "predictions" / f"{split}.parquet")

    excluded = next(iter(splits.values()))["excluded_channels"]
    if excluded:
        warnings.append(f"channels with zero fit std are excluded from macro metrics: {excluded}")
    for warning in warnings:
        reporter.log(warning, level="warning")
    p50, p95 = latency_percentiles(latencies)
    return {
        "task": "forecast",
        "splits": splits,
        "resources": {
            "load_seconds": load_seconds,
            "train_seconds": train_seconds,
            "peak_vram_mb": peak_vram_mb() if run.backbone.device == "cuda" else None,
            "latency_ms_p50": p50,
            "latency_ms_p95": p95,
            "latency_batch_size": task.eval_batch_size,
        },
        "warnings": warnings,
    }
