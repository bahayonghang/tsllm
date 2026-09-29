"""Prepared dataset summaries stored only in the dataset cache."""

from typing import Any

import polars as pl

from tsllm.config.base import duration_string
from tsllm.config.dataset import SPLIT_NAMES, DatasetConfig
from tsllm.data.types import PreparedFrame


def build_meta(prepared: PreparedFrame, cfg: DatasetConfig) -> dict[str, Any]:
    frame = prepared.frame
    eligible = frame.filter(pl.col("eligible"))
    channels: dict[str, Any] = {}
    for name in prepared.channels:
        values = eligible[name]
        channels[name] = {
            "null_rate": frame[name].null_count() / frame.height,
            "observed_count": frame.height - frame[name].null_count(),
            "eligible_count": len(values) - values.null_count(),
            "eligible_mean": values.mean(),
            "eligible_std": values.std(),
            "eligible_min": values.min(),
            "eligible_max": values.max(),
        }
    groups = (
        frame.filter(pl.col("segment_id") >= 0)
        .group_by("segment_id")
        .agg(
            pl.col("time").first().alias("start"),
            pl.col("time").last().alias("end"),
            pl.len().alias("length"),
            pl.col("eligible").sum().alias("eligible_points"),
        )
        .sort("segment_id")
    )
    segments = [
        {
            "segment_id": row["segment_id"],
            "start": row["start"].isoformat(),
            "end": row["end"].isoformat(),
            "length": row["length"],
            "duration_seconds": row["length"] * cfg.freq.total_seconds(),
            "eligible_points": row["eligible_points"],
        }
        for row in groups.iter_rows(named=True)
    ]
    splits = {}
    for name in SPLIT_NAMES:
        part = frame.filter(pl.col("split") == name)
        splits[name] = {"rows": part.height, "eligible_points": int(part["eligible"].sum())}
    return {
        "dataset_id": cfg.id,
        "freq": duration_string(cfg.freq),
        "rows": frame.height,
        "eligible_points": eligible.height,
        "observed_points": int(frame["observed"].sum()),
        "segment_count": len(segments),
        "segments": segments,
        "splits": splits,
        "split_boundaries": prepared.meta["split_boundaries"],
        "channel_names": prepared.channels,
        "channels": channels,
    }
