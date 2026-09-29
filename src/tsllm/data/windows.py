"""Legal chronological windows and adapter batches."""

import hashlib
from collections.abc import Sequence

import numpy as np
import polars as pl
from numpy.typing import NDArray

from tsllm.config.base import duration_string
from tsllm.config.dataset import SPLIT_NAMES, SplitName
from tsllm.data.types import ContextBatch, PreparedFrame, SegmentSet

type OriginRows = Sequence[int] | NDArray[np.int64]


def _manifest(
    prepared: PreparedFrame,
    split: SplitName,
    context_length: int,
    horizon: int,
    stride: int,
    max_origins: int | None = None,
) -> pl.DataFrame:
    if min(context_length, horizon, stride) < 1 or (max_origins is not None and max_origins < 1):
        raise ValueError("window lengths, stride and origin limit must be positive")
    if split not in SPLIT_NAMES:
        raise ValueError("unknown split")
    frame = prepared.frame
    origins = np.arange(context_length - 1, frame.height - horizon, dtype=np.int64)
    segments = frame["segment_id"].to_numpy()
    splits = frame["split"].to_numpy()
    left, right = origins - context_length + 1, origins + horizon
    legal = (
        (segments[left] >= 0)
        & (segments[left] == segments[right])
        & (splits[origins + 1] == split)
        & (splits[right] == split)
        & (origins % stride == 0)
    )
    origins = origins[legal]
    if max_origins is not None and origins.size > max_origins:
        origins = origins[np.linspace(0, origins.size - 1, max_origins).astype(np.int64)]
    return pl.DataFrame(
        {
            "origin_row": pl.Series(origins, dtype=pl.Int64),
            "origin_time": pl.Series(frame["time"].to_numpy()[origins], dtype=pl.Datetime("us")),
            "segment_id": pl.Series(segments[origins], dtype=pl.Int32),
            "split": pl.Series([split] * origins.size, dtype=pl.Categorical),
        }
    )


def build_train_manifest(
    prepared: PreparedFrame,
    context_length: int,
    horizon: int,
    stride: int = 1,
) -> pl.DataFrame:
    return _manifest(prepared, "fit", context_length, horizon, stride)


def build_eval_manifest(
    prepared: PreparedFrame,
    split: SplitName,
    context_length: int,
    horizon: int,
    stride: int = 1,
    max_eval_origins: int | None = None,
) -> pl.DataFrame:
    return _manifest(prepared, split, context_length, horizon, stride, max_eval_origins)


def validate_origins(
    prepared: PreparedFrame,
    origin_rows: OriginRows,
    context_length: int,
    horizon: int,
    *,
    require_target_split: bool = False,
) -> NDArray[np.int64]:
    origins = np.asarray(origin_rows)
    if origins.ndim != 1 or (origins.size and not np.issubdtype(origins.dtype, np.integer)):
        raise ValueError("origins must be a one-dimensional integer array")
    if context_length < 1 or horizon < 0:
        raise ValueError("window lengths are invalid")
    origins = origins.astype(np.int64)
    left, right = origins - context_length + 1, origins + horizon
    if np.any(left < 0) or np.any(right >= prepared.frame.height):
        raise ValueError("window exceeds dataset bounds")
    segments = prepared.frame["segment_id"].to_numpy()
    if np.any(segments[left] < 0) or np.any(segments[left] != segments[right]):
        raise ValueError("window crosses a segment boundary")
    if require_target_split and horizon:
        splits = prepared.frame["split"].to_numpy()
        if np.any(splits[origins + 1] != splits[right]):
            raise ValueError("target window crosses a split boundary")
    return origins


def context_batch(
    prepared: PreparedFrame, origin_rows: OriginRows, context_length: int
) -> ContextBatch:
    origins = validate_origins(prepared, origin_rows, context_length, 0)
    rows = origins[:, None] + np.arange(1 - context_length, 1)
    values = prepared.frame.select(prepared.channels).to_numpy().astype(np.float32)
    return ContextBatch(
        values[rows].transpose(0, 2, 1),
        list(prepared.channels),
        prepared.frame["time"].to_numpy()[origins].astype("datetime64[us]"),
        duration_string(prepared.freq),
    )


def targets(
    prepared: PreparedFrame,
    origin_rows: OriginRows,
    horizon: int,
) -> tuple[NDArray[np.float32], NDArray[np.bool_]]:
    if horizon < 1:
        raise ValueError("horizon must be positive")
    origins = validate_origins(prepared, origin_rows, 1, horizon, require_target_split=True)
    rows = origins[:, None] + np.arange(1, horizon + 1)
    values = prepared.frame.select(prepared.channels).to_numpy().astype(np.float32)
    batch = values[rows].transpose(0, 2, 1)
    return batch, ~np.isnan(batch)


def segment_set(prepared: PreparedFrame, split: SplitName, min_rows: int = 1) -> SegmentSet:
    if min_rows < 1 or split not in SPLIT_NAMES:
        raise ValueError("invalid segment selection")
    frame = prepared.frame.filter((pl.col("split") == split) & (pl.col("segment_id") >= 0))
    arrays = []
    for part in frame.partition_by("segment_id", maintain_order=True):
        if part.height >= min_rows:
            arrays.append(part.select(prepared.channels).to_numpy().astype(np.float32).T)
    return SegmentSet(arrays, list(prepared.channels), duration_string(prepared.freq))


def origin_set_hash(manifest: pl.DataFrame) -> str:
    times = manifest["origin_time"].cast(pl.Int64).to_numpy().astype("<i8")
    return hashlib.sha256(times.tobytes()).hexdigest()[:12]
