"""Data containers shared with tasks and adapters."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import polars as pl
from numpy.typing import NDArray


@dataclass(frozen=True)
class PreparedFrame:
    frame: pl.DataFrame
    channels: list[str]
    freq: timedelta
    meta: dict[str, Any]


@dataclass(frozen=True)
class ContextBatch:
    values: NDArray[np.float32]  # (B, C, L), missing values are NaN.
    channel_names: list[str]
    origin_time: NDArray[np.datetime64]  # (B,), datetime64[us].
    freq: str


@dataclass(frozen=True)
class SegmentSet:
    arrays: list[NDArray[np.float32]]  # Each (C, T_i), missing values are NaN.
    channel_names: list[str]
    freq: str
