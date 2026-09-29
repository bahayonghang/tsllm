"""Fit-only threshold resolution and future-only event labels."""

import math

import numpy as np
import polars as pl
from numpy.typing import NDArray

from tsllm.config.labels import FutureEventRule, OutsideThreshold, ThresholdSpec
from tsllm.data.registry import DatasetConfigError
from tsllm.data.stats import fit_rows
from tsllm.data.types import PreparedFrame
from tsllm.data.windows import OriginRows, validate_origins

type ResolvedThreshold = float | tuple[float, float]


def _resolve(prepared: PreparedFrame, channel: str, spec: ThresholdSpec | float) -> float:
    if isinstance(spec, (float, int)):
        value = spec
    elif spec.value is not None:
        value = spec.value
    else:
        assert spec.quantile is not None
        value = (
            fit_rows(prepared)[channel]
            .cast(pl.Float64)
            .fill_nan(None)
            .quantile(spec.quantile, interpolation="linear")
        )
    if value is None or not math.isfinite(value):
        raise DatasetConfigError(f"channel '{channel}' has no finite label threshold")
    return float(value)


def resolve_threshold(prepared: PreparedFrame, spec: FutureEventRule) -> ResolvedThreshold:
    if spec.channel not in prepared.channels:
        raise DatasetConfigError(f"label channel '{spec.channel}' is not selected")
    if isinstance(spec.threshold, OutsideThreshold):
        low = _resolve(prepared, spec.channel, spec.threshold.low)
        high = _resolve(prepared, spec.channel, spec.threshold.high)
        if low >= high:
            raise DatasetConfigError("outside label thresholds must be ordered")
        return low, high
    return _resolve(prepared, spec.channel, spec.threshold)


def future_event_labels(
    prepared: PreparedFrame,
    origin_rows: OriginRows,
    rule: FutureEventRule,
    threshold: ResolvedThreshold,
) -> NDArray[np.int8]:
    if rule.channel not in prepared.channels:
        raise DatasetConfigError(f"label channel '{rule.channel}' is not selected")
    origins = validate_origins(prepared, origin_rows, 1, rule.window, require_target_split=True)
    rows = origins[:, None] + np.arange(1, rule.window + 1)
    values = prepared.frame[rule.channel].to_numpy()[rows]
    if rule.op == "outside":
        if not isinstance(threshold, tuple) or threshold[0] >= threshold[1]:
            raise ValueError("outside threshold must be an ordered pair")
        condition = (values < threshold[0]) | (values > threshold[1])
    else:
        if isinstance(threshold, tuple):
            raise ValueError("comparison threshold must be scalar")
        condition = values > threshold if rule.op == "gt" else values < threshold
    condition &= ~np.isnan(values)
    cumulative = np.pad(np.cumsum(condition, axis=1), ((0, 0), (1, 0)))
    duration = rule.min_duration
    consecutive = cumulative[:, duration:] - cumulative[:, :-duration]
    return (consecutive >= duration).any(axis=1).astype(np.int8)
