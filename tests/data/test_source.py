import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import dump_yaml
from tsllm.data.registry import DatasetConfigError, DatasetNotFound, list_datasets, load_dataset
from tsllm.data.source import read_source


def test_late_floats_and_dedup(synthetic_config: DatasetConfig) -> None:
    frame = read_source(synthetic_config)
    assert frame.schema["late"] == pl.Float64
    assert frame["late"].head(2000).null_count() == 2000
    assert frame["time"].is_sorted()
    assert frame.height == 25920 - 180 - 18


@pytest.mark.parametrize(("policy", "expected"), [("keep_first", 1.0), ("keep_last", 2.0)])
def test_dedup_policy(
    config_factory: Callable[..., DatasetConfig], policy: str, expected: float
) -> None:
    cfg = config_factory(dedup=policy)
    pl.DataFrame({"date": [datetime(2024, 1, 1)] * 2, "x": [1.0, 2.0]}).write_csv(cfg.source.path)
    assert read_source(cfg)["x"].item() == expected


def test_auto_numeric_discovery(config_factory: Callable[..., DatasetConfig]) -> None:
    cfg = config_factory()
    pl.DataFrame(
        {
            "date": [datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(2100)],
            "x": [1] * 2100,
            "late": [None] * 2000 + [3.5] * 100,
            "empty": [None] * 2100,
            "identifier": ["line-A"] * 2100,
            "mixed": ["1"] * 2099 + ["not-numeric"],
        }
    ).write_csv(cfg.source.path)
    result = read_source(cfg)
    assert result.columns == ["time", "x", "late", "empty"]
    assert all(result.schema[name] == pl.Float64 for name in result.columns[1:])


@pytest.mark.parametrize("channels", [None, [{"name": "x"}]])
def test_numeric_timestamp_uses_configured_format(
    config_factory: Callable[..., DatasetConfig],
    tmp_path: Path,
    channels: list[dict[str, str]] | None,
) -> None:
    cfg = config_factory(
        source={
            "path": str(tmp_path / "source.csv"),
            "time_column": "date",
            "time_format": "%Y%m%d",
        },
        channels=channels,
    )
    cfg.source.path.write_text("date,x\n20240101,1\n20240102,2\n", encoding="utf-8")
    frame = read_source(cfg)
    assert frame["time"].to_list() == [datetime(2024, 1, 1), datetime(2024, 1, 2)]
    assert frame.schema["time"] == pl.Datetime("us")


def test_invalid_explicit_value_has_no_traceback_leak(
    config_factory: Callable[..., DatasetConfig],
) -> None:
    cfg = config_factory(channels=[{"name": "x"}])
    sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
    pl.DataFrame({"date": [datetime(2024, 1, 1)], "x": [sentinel]}).write_csv(cfg.source.path)
    with pytest.raises(DatasetConfigError) as exc:
        read_source(cfg)
    assert sentinel not in "".join(traceback.format_exception(exc.value))


def test_lossy_encoding(config_factory: Callable[..., DatasetConfig]) -> None:
    cfg = config_factory()
    data = b"date,x,label\n2024-01-01T00:00:00,1," + bytes([255])
    cfg.source.path.write_bytes(data)
    with pytest.raises(DatasetConfigError):
        read_source(cfg)
    cfg = cfg.model_copy(
        update={"source": cfg.source.model_copy(update={"encoding": "utf8-lossy"})}
    )
    assert read_source(cfg).columns == ["time", "x"]


def test_parquet_types(config_factory: Callable[..., DatasetConfig], tmp_path: Path) -> None:
    cfg = config_factory(
        source={
            "path": str(tmp_path / "source.parquet"),
            "time_column": "date",
            "format": "parquet",
        }
    )
    pl.DataFrame(
        {"date": [datetime(2024, 1, 1)], "x": [1], "empty": [None], "label": ["A"]}
    ).write_parquet(cfg.source.path)
    result = read_source(cfg)
    assert result.columns == ["time", "x", "empty"]
    assert result.schema["x"] == pl.Float64


def test_registry(config_factory: Callable[..., DatasetConfig], tmp_path: Path) -> None:
    cfg = config_factory()
    dump_yaml(cfg, tmp_path / "synthetic.yaml")
    assert load_dataset("synthetic", tmp_path) == cfg
    assert list_datasets(tmp_path) == [cfg]
    with pytest.raises(DatasetNotFound):
        load_dataset("missing", tmp_path)
    dump_yaml(cfg, tmp_path / "mismatch.yaml")
    with pytest.raises(DatasetConfigError):
        load_dataset("mismatch", tmp_path)


def test_registry_sanitizes_yaml_errors(tmp_path: Path) -> None:
    sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
    (tmp_path / "broken.yaml").write_text("bad: [" + sentinel, encoding="utf-8")
    with pytest.raises(DatasetConfigError) as exc:
        load_dataset("broken", tmp_path)
    assert sentinel not in "".join(traceback.format_exception(exc.value))


def test_empty_source_rejected(config_factory: Callable[..., DatasetConfig]) -> None:
    cfg = config_factory()
    cfg.source.path.write_text("date,x\n", encoding="utf-8")
    with pytest.raises(DatasetConfigError):
        read_source(cfg)


def test_ignored_mixed_column_does_not_affect_read(
    config_factory: Callable[..., DatasetConfig],
) -> None:
    cfg = config_factory(channels=[{"name": "x"}, {"name": "label", "role": "ignore"}])
    pl.DataFrame(
        {
            "date": [datetime(2024, 1, 1) + timedelta(seconds=i) for i in range(201)],
            "x": [1] * 201,
            "label": ["1"] * 200 + ["mixed"],
        }
    ).write_csv(cfg.source.path)
    assert read_source(cfg).columns == ["time", "x"]
