from collections.abc import Callable
from datetime import datetime, timedelta

import polars as pl
import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.data.prepare import resample


def source(seconds: list[int], values: list[float | None]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "time": [datetime(2024, 1, 1) + timedelta(seconds=s) for s in seconds],
            "x": values,
        },
        schema_overrides={"x": pl.Float64},
    )


def test_right_edge_is_causal(config_factory: Callable[..., DatasetConfig]) -> None:
    cfg = config_factory()
    frame = source([0, 10, 60, 61], [1, 3, 5, 99])
    result = resample(frame, cfg)
    assert result["time"].to_list() == [
        datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(3)
    ]
    assert result["x"].to_list() == pytest.approx([1, 4, 99])
    assert result.schema["x"] == pl.Float32
    assert result.schema["time"] == pl.Datetime("us")


def test_grid_and_observed(config_factory: Callable[..., DatasetConfig]) -> None:
    result = resample(source([0, 120], [None, 3]), config_factory())
    assert result["observed"].to_list() == [True, False, True]
    assert result["x"].to_list() == [None, None, 3]


def test_native_grid_ceiling(config_factory: Callable[..., DatasetConfig]) -> None:
    result = resample(source([0, 1, 10, 31], [1, 2, 4, 8]), config_factory(freq="10s"))
    assert result["x"].to_list() == [1, 3, None, None, 8]
    assert result["observed"].to_list() == [True, True, False, False, True]


def test_last_keeps_missing(config_factory: Callable[..., DatasetConfig]) -> None:
    result = resample(source([10, 60], [2, None]), config_factory(aggregation="last"))
    assert result["x"].to_list() == [None]
