from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from tsllm.config.base import parse_duration
from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import dump_yaml, load_yaml


@pytest.mark.parametrize(("text", "seconds"), [("10s", 10), ("1min", 60), ("6h", 21600)])
def test_duration(text: str, seconds: int) -> None:
    assert parse_duration(text) == timedelta(seconds=seconds)


@pytest.mark.parametrize("value", ["0s", "-1s", "1month", 60])
def test_invalid_duration(value: object) -> None:
    with pytest.raises(ValueError):
        parse_duration(value)


def test_config_round_trip_and_strict_fields(tmp_path: Path) -> None:
    values = {
        "id": "synthetic",
        "source": {"path": "synthetic.csv", "time_column": "date"},
        "native_freq": "10s",
        "freq": "1min",
        "segments": {"max_gap": "2min", "min_length": "6h"},
        "channels": [{"name": "合成通道"}],
    }
    cfg = DatasetConfig.model_validate(values)
    path = tmp_path / "config.yaml"
    dump_yaml(cfg, path)
    assert load_yaml(DatasetConfig, path) == cfg
    assert "合成通道" in path.read_text(encoding="utf-8")
    with pytest.raises(ValidationError):
        DatasetConfig.model_validate(values | {"unknown": True})
    with pytest.raises(ValidationError):
        DatasetConfig.model_validate(
            values | {"source": {"path": "x", "time_column": "t", "typo": 1}}
        )
    with pytest.raises(ValidationError):
        DatasetConfig.model_validate(values | {"split": {"ratios": [1, 1, 1, 1]}})
