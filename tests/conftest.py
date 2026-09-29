"""Synthetic source fixtures. Tests never read private datasets."""

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.data.types import PreparedFrame


@pytest.fixture
def config_factory(tmp_path: Path) -> Callable[..., DatasetConfig]:
    def make(**overrides: Any) -> DatasetConfig:
        payload = {
            "id": "synthetic",
            "source": {"path": str(tmp_path / "source.csv"), "time_column": "date"},
            "native_freq": "10s",
            "freq": "1min",
            "segments": {"max_gap": "2min", "min_length": "1min"},
        }
        return DatasetConfig.model_validate(payload | overrides)

    return make


def make_synthetic_csv(tmp_path: Path) -> tuple[Path, DatasetConfig]:
    n = 3 * 24 * 60 * 6
    rows = np.arange(n)
    start = datetime(2024, 1, 1)
    signal = rows.astype(float) % 97
    operating = np.ones(n)
    operating[(rows >= 36 * 360) & (rows < 40 * 360)] = 0
    frame = pl.DataFrame(
        {
            "date": [start + timedelta(seconds=int(i) * 10) for i in rows],
            "late": [None if i < 2000 else float(signal[i]) for i in rows],
            "operating": operating,
            "signal": signal,
            "row": rows,
        }
    )
    frame = frame.filter(
        ~pl.col("row").is_between(4000, 4179)
        & ~pl.col("row").is_between(6000, 6008)
        & ~pl.col("row").is_between(8000, 8008)
    ).drop("row")
    frame = pl.concat([frame, frame.head(3)])
    path = tmp_path / "synthetic.csv"
    frame.write_csv(path)
    cfg = DatasetConfig.model_validate(
        {
            "id": "synthetic",
            "source": {"path": str(path), "time_column": "date"},
            "native_freq": "10s",
            "freq": "1min",
            "channels": [{"name": name} for name in ["late", "operating", "signal"]],
            "eligibility": {"all": [{"channel": "operating", "op": "gt", "value": 0.5}]},
            "segments": {"max_gap": "2min", "min_length": "6h"},
        }
    )
    return path, cfg


@pytest.fixture
def synthetic_config(tmp_path: Path) -> DatasetConfig:
    return make_synthetic_csv(tmp_path)[1]


@pytest.fixture
def prepared_frame() -> PreparedFrame:
    n = 100
    values = [None if i in [15, 70] else float(i) for i in range(n)]
    frame = pl.DataFrame(
        {
            "time": [datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(n)],
            "x": values,
            "y": [float(2 * i) for i in range(n)],
            "observed": [True] * n,
            "eligible": [i != 10 for i in range(n)],
            "segment_id": [0] * 30 + [-1] * 3 + [1] * 67,
            "split": ["fit"] * 60 + ["val"] * 15 + ["cal"] * 10 + ["test"] * 15,
        }
    ).with_columns(
        pl.col("x", "y").cast(pl.Float32),
        pl.col("segment_id").cast(pl.Int32),
        pl.col("split").cast(pl.Categorical),
    )
    return PreparedFrame(frame, ["x", "y"], timedelta(minutes=1), {})
