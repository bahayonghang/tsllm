"""Causal grid aggregation and dataset preparation."""

import math
from datetime import timedelta
from pathlib import Path

import numpy as np
import polars as pl

from tsllm.config.dataset import SPLIT_NAMES, DatasetConfig, SegmentConfig, SplitConfig
from tsllm.data.cache import cache_dir, is_fresh, read_cache, source_fingerprint, write_cache
from tsllm.data.registry import DatasetConfigError
from tsllm.data.rules import evaluate
from tsllm.data.source import read_source
from tsllm.data.types import PreparedFrame
from tsllm.reporting import Reporter


def resample(frame: pl.DataFrame, cfg: DatasetConfig) -> pl.DataFrame:
    if frame.is_empty():
        raise DatasetConfigError(f"dataset '{cfg.id}' has no source rows")
    channels = [name for name in frame.columns if name != "time"]
    expressions = [
        (pl.col(name).mean() if cfg.aggregation == "mean" else pl.col(name).last())
        .cast(pl.Float32)
        .alias(name)
        for name in channels
    ] + [pl.len().alias("_n")]
    if cfg.freq == cfg.native_freq:
        lower = pl.col("time").dt.truncate(cfg.freq)
        aligned = pl.when(pl.col("time") == lower).then(lower).otherwise(lower + cfg.freq)
        grouped = (
            frame.with_columns(aligned.alias("time")).group_by("time").agg(expressions).sort("time")
        )
    else:
        grouped = frame.group_by_dynamic("time", every=cfg.freq, closed="right", label="right").agg(
            expressions
        )
    grid = pl.DataFrame(
        {
            "time": pl.datetime_range(
                grouped["time"][0],
                grouped["time"][-1],
                interval=cfg.freq,
                time_unit="us",
                eager=True,
            )
        }
    )
    return (
        grid.join(grouped, on="time", how="left")
        .with_columns((pl.col("_n").fill_null(0) > 0).alias("observed"))
        .drop("_n")
    )


def assign_segments(frame: pl.DataFrame, freq: timedelta, cfg: SegmentConfig) -> pl.DataFrame:
    points = np.flatnonzero(frame["eligible"].to_numpy())
    ids = np.full(frame.height, -1, dtype=np.int32)
    if points.size:
        cuts = (
            np.flatnonzero(
                (np.diff(points) - 1) * (freq / timedelta(microseconds=1))
                > cfg.max_gap / timedelta(microseconds=1)
            )
            + 1
        )
        starts = np.r_[0, cuts]
        stops = np.r_[cuts - 1, points.size - 1]
        next_id = 0
        for start, stop in zip(starts, stops, strict=True):
            first, last = int(points[start]), int(points[stop])
            if (last - first + 1) * freq >= cfg.min_length:
                ids[first : last + 1] = next_id
                next_id += 1
    return frame.with_columns(pl.Series("segment_id", ids))


def assign_splits(frame: pl.DataFrame, cfg: SplitConfig) -> tuple[pl.DataFrame, dict[str, str]]:
    points = np.flatnonzero(frame["eligible"].to_numpy())
    if not points.size:
        raise DatasetConfigError("dataset has no eligible points for chronological splits")
    ranks = [max(0, math.ceil(float(r) * points.size) - 1) for r in np.cumsum(cfg.ratios)[:3]]
    boundaries = points[ranks]
    indices = np.searchsorted(boundaries, np.arange(frame.height), side="right")
    split = pl.Series("split", np.asarray(SPLIT_NAMES)[indices]).cast(pl.Categorical)
    times = {
        name: frame["time"][int(row)].isoformat()
        for name, row in zip(SPLIT_NAMES[1:], boundaries, strict=True)
    }
    return frame.with_columns(split), times


def prepare(cfg: DatasetConfig, reporter: Reporter | None = None) -> PreparedFrame:
    if reporter is not None:
        reporter.stage("read")
    source = read_source(cfg)
    channels = source.columns[1:]
    if reporter is not None:
        reporter.stage("resample")
    frame = resample(source, cfg)
    frame = frame.with_columns(evaluate(cfg.eligibility, frame, channels))
    if reporter is not None:
        reporter.stage("segment")
    frame = assign_segments(frame, cfg.freq, cfg.segments)
    if reporter is not None:
        reporter.stage("split")
    frame, boundaries = assign_splits(frame, cfg.split)
    return PreparedFrame(frame, channels, cfg.freq, {"split_boundaries": boundaries})


def ingest_dataset(
    cfg: DatasetConfig,
    reporter: Reporter,
    *,
    force: bool = False,
    cache_root: Path | None = None,
) -> PreparedFrame:
    """Reuse a fresh cache or prepare and store the configured dataset."""
    if not force and is_fresh(cfg, cache_root):
        prepared = read_cache(cfg, cache_root)
        reporter.log(f"dataset '{cfg.id}' reused its current cache")
        reporter.stage("done")
        return prepared
    try:
        initial_source = source_fingerprint(cfg)
        prepared = prepare(cfg, reporter)
        if source_fingerprint(cfg) != initial_source:
            raise DatasetConfigError(f"dataset '{cfg.id}' source changed during ingestion; retry")
        reporter.stage("write")
        prepared = write_cache(cfg, prepared, cache_root)
        if prepared.meta["source"] != initial_source or source_fingerprint(cfg) != initial_source:
            # A changed source must not make an older frame look fresh.
            (cache_dir(cfg, cache_root) / "meta.json").unlink(missing_ok=True)
            raise DatasetConfigError(f"dataset '{cfg.id}' source changed during ingestion; retry")
    except OSError:
        raise DatasetConfigError(f"dataset '{cfg.id}' source or cache cannot be accessed") from None
    reporter.stage("done")
    return prepared
