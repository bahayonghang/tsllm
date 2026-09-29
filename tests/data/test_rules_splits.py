from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

from tsllm.config.dataset import ConditionGroup, DatasetConfig, SegmentConfig, SplitConfig
from tsllm.data.prepare import assign_segments, assign_splits, prepare
from tsllm.data.registry import DatasetConfigError
from tsllm.data.rules import evaluate


def grid(eligible: list[bool]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "time": [datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(len(eligible))],
            "eligible": eligible,
        }
    )


def test_gap_means_internal_interruption() -> None:
    cfg = SegmentConfig.model_validate({"max_gap": "2min", "min_length": "1min"})
    frame = grid([False, True, False, False, True, False, False, False, True, False])
    result = assign_segments(frame, timedelta(minutes=1), cfg)
    assert result["segment_id"].to_list() == [-1, 0, 0, 0, 0, -1, -1, -1, 1, -1]
    assert result.schema["segment_id"] == pl.Int32


def test_min_length_includes_grid_steps() -> None:
    cfg = SegmentConfig.model_validate({"max_gap": "1min", "min_length": "3min"})
    result = assign_segments(
        grid([True, True, False, False, True, True, True]), timedelta(minutes=1), cfg
    )
    assert result["segment_id"].to_list() == [-1, -1, -1, -1, 0, 0, 0]


def test_split_counts_and_boundaries() -> None:
    eligible = [i % 3 != 0 for i in range(311)]
    original = grid(eligible)
    frame, boundaries = assign_splits(original, SplitConfig())
    n = sum(eligible)
    ratios = [0.7, 0.1, 0.1, 0.1]
    counts = [
        frame.filter(pl.col("eligible") & (pl.col("split") == s)).height
        for s in ["fit", "val", "cal", "test"]
    ]
    assert all(abs(count - ratio * n) <= 1 for count, ratio in zip(counts, ratios, strict=True))
    assert frame["split"].null_count() == 0
    assert frame.schema["split"] == pl.Categorical
    for name, time in boundaries.items():
        assert frame.filter(pl.col("time") == datetime.fromisoformat(time))["split"].item() == name


@pytest.mark.parametrize(
    ("op", "expected"),
    [
        ("gt", [False, False, True, False]),
        ("ge", [False, True, True, False]),
        ("lt", [True, False, False, False]),
        ("le", [True, True, False, False]),
        ("eq", [False, True, False, False]),
        ("ne", [True, False, True, False]),
    ],
)
def test_conditions(op: str, expected: list[bool]) -> None:
    rule = ConditionGroup.model_validate({"all": [{"channel": "x", "op": op, "value": 2}]})
    assert evaluate(rule, pl.DataFrame({"x": [1, 2, 3, None]}), ["x"]).to_list() == expected


def test_nested_any_and_all() -> None:
    rule = ConditionGroup.model_validate(
        {
            "any": [
                {
                    "all": [
                        {"channel": "x", "op": "gt", "value": 2},
                        {"channel": "y", "op": "eq", "value": 1},
                    ]
                },
                {"channel": "x", "op": "lt", "value": 0},
            ]
        }
    )
    assert evaluate(
        rule, pl.DataFrame({"x": [3, -1, None], "y": [1, None, 1]}), ["x", "y"]
    ).to_list() == [True, True, False]


def test_no_eligibility_rule() -> None:
    assert evaluate(
        None, pl.DataFrame({"x": [None, 1, None], "y": [None, None, 1]}), ["x", "y"]
    ).to_list() == [False, True, True]
    with pytest.raises(DatasetConfigError):
        assign_splits(grid([False, False]), SplitConfig())


def test_pipeline_segments(synthetic_config: DatasetConfig) -> None:
    result = prepare(synthetic_config)
    assert result.frame.columns == [
        "time",
        "late",
        "operating",
        "signal",
        "observed",
        "eligible",
        "segment_id",
        "split",
    ]
    assert len(result.meta["split_boundaries"]) == 3
    assert result.frame["segment_id"].n_unique() >= 3
    assert not np.isnan(result.frame["observed"].to_numpy()).any()
