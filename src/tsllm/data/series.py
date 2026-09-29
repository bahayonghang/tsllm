"""Bucket means of a prepared frame for plotting."""

import math
from datetime import datetime
from typing import Any

import polars as pl

from tsllm.config.base import duration_string
from tsllm.data.registry import ChannelError
from tsllm.data.types import PreparedFrame


def _naive(value: datetime | None) -> datetime | None:
    # Prepared times have no time zone. A request offset is ignored, not converted.
    return None if value is None else value.replace(tzinfo=None)


def downsample_series(
    prepared: PreparedFrame,
    channels: list[str] | None,
    start: datetime | None,
    end: datetime | None,
    max_points: int,
) -> dict[str, Any]:
    """Equal-width time buckets over [start, end], at most max_points buckets.

    Each bucket gives the mean of non-null values and is labelled with its start time.
    Segments that overlap the range and the split boundaries come from the cache metadata.
    """
    names = channels or prepared.channels
    unknown = [name for name in names if name not in prepared.channels]
    if unknown:
        dataset = prepared.meta.get("dataset_id")
        raise ChannelError(f"dataset '{dataset}' has no channel '{unknown[0]}'")
    start, end = _naive(start), _naive(end)
    frame = prepared.frame.select("time", *names)
    if start is not None:
        frame = frame.filter(pl.col("time") >= start)
    if end is not None:
        frame = frame.filter(pl.col("time") <= end)
    every = prepared.freq
    if frame.height > 0:
        steps = (frame["time"].max() - frame["time"].min()) // prepared.freq + 1  # type: ignore[operator]
        every = prepared.freq * max(1, math.ceil(steps / max_points))
        if every > prepared.freq:
            frame = frame.group_by_dynamic("time", every=every, start_by="datapoint").agg(
                pl.col(names).mean()
            )
    frame = frame.with_columns(pl.col(names).cast(pl.Float64).fill_nan(None))
    segments = [
        segment
        for segment in prepared.meta.get("segments", [])
        if (end is None or datetime.fromisoformat(segment["start"]) <= end)
        and (start is None or datetime.fromisoformat(segment["end"]) >= start)
    ]
    return {
        "every": duration_string(every),
        "time": frame["time"].to_list(),
        "values": {name: frame[name].to_list() for name in names},
        "segments": segments,
        "split_boundaries": prepared.meta.get("split_boundaries", {}),
    }
