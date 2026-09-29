from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from pydantic import ValidationError

from tsllm.config.labels import FutureEventRule
from tsllm.data.labels import future_event_labels, resolve_threshold
from tsllm.data.registry import DatasetConfigError
from tsllm.data.types import PreparedFrame


def rule(**kwargs: object) -> FutureEventRule:
    return FutureEventRule.model_validate(
        {
            "channel": "x",
            "op": "gt",
            "threshold": {"quantile": 0.95},
            "window": 4,
            "min_duration": 2,
        }
        | kwargs
    )


@pytest.mark.parametrize("split", ["val", "cal", "test"])
def test_threshold_ignores_future(prepared_frame: PreparedFrame, split: str) -> None:
    baseline = resolve_threshold(prepared_frame, rule())
    altered = prepared_frame.frame.with_columns(
        pl.when(pl.col("split") == split).then(1e12).otherwise(pl.col("x")).alias("x")
    )
    assert resolve_threshold(replace(prepared_frame, frame=altered), rule()) == baseline


def test_threshold_ignores_ineligible_fit(prepared_frame: PreparedFrame) -> None:
    baseline = resolve_threshold(prepared_frame, rule(threshold={"quantile": 0.5}))
    altered = prepared_frame.frame.with_columns(
        pl.when(~pl.col("eligible")).then(1e12).otherwise(pl.col("x")).alias("x")
    )
    assert (
        resolve_threshold(replace(prepared_frame, frame=altered), rule(threshold={"quantile": 0.5}))
        == baseline
    )
    expected = np.quantile([i for i in range(60) if i not in [10, 15]], 0.5)
    assert baseline == pytest.approx(expected)


def test_labels_require_consecutive_future_steps(prepared_frame: PreparedFrame) -> None:
    values = [9, 9, 9, 0, 0, 9, 0, 9, 0, 9, 9, 0] + [0] * 88
    changed = replace(
        prepared_frame,
        frame=prepared_frame.frame.with_columns(pl.Series("x", values, dtype=pl.Float32)),
    )
    labels = future_event_labels(changed, [2, 5, 7], rule(threshold={"value": 5}), 5.0)
    assert labels.dtype == np.int8
    assert labels.tolist() == [0, 0, 1]


@pytest.mark.parametrize(("event_row", "expected"), [(4, 0), (5, 0), (6, 1), (9, 1), (10, 0)])
def test_labels_use_exact_future_interval(
    prepared_frame: PreparedFrame, event_row: int, expected: int
) -> None:
    values = [0.0] * prepared_frame.frame.height
    values[event_row] = 9.0
    changed = replace(
        prepared_frame,
        frame=prepared_frame.frame.with_columns(pl.Series("x", values, dtype=pl.Float32)),
    )
    labels = future_event_labels(changed, [5], rule(threshold={"value": 5}, min_duration=1), 5.0)
    assert labels.tolist() == [expected]


def test_null_breaks_duration(prepared_frame: PreparedFrame) -> None:
    values = [0.0, 9, None, 9, 0] + [0] * 95
    changed = replace(
        prepared_frame,
        frame=prepared_frame.frame.with_columns(pl.Series("x", values, dtype=pl.Float32)),
    )
    assert future_event_labels(changed, [0], rule(), 5.0).tolist() == [0]


@pytest.mark.parametrize(
    ("op", "threshold", "expected"),
    [
        ("gt", 2.0, 1),
        ("lt", 3.0, 1),
        ("outside", (1.5, 3.5), 0),
    ],
)
def test_comparison_operators(
    prepared_frame: PreparedFrame, op: str, threshold: float | tuple[float, float], expected: int
) -> None:
    config = {"low": 1.5, "high": 3.5} if op == "outside" else {"value": threshold}
    labels = future_event_labels(prepared_frame, [0], rule(op=op, threshold=config), threshold)
    assert labels.tolist() == [expected]


def test_outside_threshold_resolution(prepared_frame: PreparedFrame) -> None:
    fixed = rule(op="outside", threshold={"low": 1, "high": 2})
    assert resolve_threshold(prepared_frame, fixed) == (1.0, 2.0)
    fitted = rule(op="outside", threshold={"low": {"quantile": 0.05}, "high": {"quantile": 0.95}})
    threshold = resolve_threshold(prepared_frame, fitted)
    assert isinstance(threshold, tuple) and threshold[0] < threshold[1]
    with pytest.raises(DatasetConfigError):
        resolve_threshold(prepared_frame, rule(op="outside", threshold={"low": 3, "high": 2}))


def test_illegal_label_window_rejected(prepared_frame: PreparedFrame) -> None:
    with pytest.raises(ValueError, match="segment"):
        future_event_labels(prepared_frame, [28], rule(), 1.0)
    with pytest.raises(ValueError, match="split"):
        future_event_labels(prepared_frame, [58], rule(), 1.0)
    assert future_event_labels(prepared_frame, [], rule(), 1.0).shape == (0,)


def test_invalid_rule_and_empty_fit_channel(prepared_frame: PreparedFrame) -> None:
    with pytest.raises(ValidationError):
        rule(min_duration=5)
    with pytest.raises(ValidationError):
        rule(threshold={"value": 1, "quantile": 0.9})
    with pytest.raises(ValidationError):
        rule(op="outside")
    empty = replace(
        prepared_frame,
        frame=prepared_frame.frame.with_columns(pl.lit(None, dtype=pl.Float32).alias("x")),
    )
    with pytest.raises(DatasetConfigError):
        resolve_threshold(empty, rule())
