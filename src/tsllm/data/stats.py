"""Statistics from eligible fit rows only."""

from dataclasses import dataclass
from typing import cast

import polars as pl

from tsllm.data.registry import DatasetConfigError
from tsllm.data.types import PreparedFrame

QUANTILES = (0.01, 0.05, 0.5, 0.95, 0.99)


@dataclass(frozen=True)
class ChannelStats:
    count: int
    mean: float | None
    std: float | None
    quantiles: dict[str, float | None]


@dataclass(frozen=True)
class FitStats:
    channels: dict[str, ChannelStats]


def fit_rows(prepared: PreparedFrame) -> pl.DataFrame:
    frame = prepared.frame.filter((pl.col("split") == "fit") & pl.col("eligible"))
    if frame.is_empty():
        raise DatasetConfigError("dataset has no eligible fit rows")
    return frame


def compute_fit_stats(prepared: PreparedFrame) -> FitStats:
    frame = fit_rows(prepared)
    result = {}
    for name in prepared.channels:
        values = frame[name].cast(pl.Float64).fill_nan(None)
        result[name] = ChannelStats(
            count=len(values) - values.null_count(),
            mean=cast(float | None, values.mean()),
            std=cast(float | None, values.std(ddof=1)),
            quantiles={str(q): values.quantile(q, interpolation="linear") for q in QUANTILES},
        )
    return FitStats(result)
