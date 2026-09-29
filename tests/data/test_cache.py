import os
from pathlib import Path

import polars as pl
import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.data.cache import (
    DatasetNotIngested,
    cache_dir,
    config_hash,
    is_fresh,
    read_cache,
    write_cache,
)
from tsllm.data.prepare import prepare


def test_cache_round_trip_and_profile(synthetic_config: DatasetConfig, tmp_path: Path) -> None:
    root = tmp_path / "cache"
    assert not is_fresh(synthetic_config, root)
    with pytest.raises(DatasetNotIngested):
        read_cache(synthetic_config, root)
    prepared = prepare(synthetic_config)
    written = write_cache(synthetic_config, prepared, root)
    assert is_fresh(synthetic_config, root)
    loaded = read_cache(synthetic_config, root)
    assert loaded.frame.equals(prepared.frame)
    assert loaded.meta == written.meta
    assert loaded.meta["eligible_points"] == int(prepared.frame["eligible"].sum())
    assert (
        sum(s["eligible_points"] for s in loaded.meta["splits"].values())
        == loaded.meta["eligible_points"]
    )
    assert loaded.meta["channels"]["late"]["null_rate"] > 0
    assert not list(cache_dir(synthetic_config, root).glob("*.tmp"))
    assert loaded.frame.schema["split"] == pl.Categorical


def test_hash_excludes_display_metadata(synthetic_config: DatasetConfig) -> None:
    payload = synthetic_config.model_dump(mode="json")
    payload["channels"][0]["unit"] = "synthetic-unit"
    payload["channels"][0]["description"] = "Synthetic description"
    assert config_hash(DatasetConfig.model_validate(payload)) == config_hash(synthetic_config)
    payload["channels"][0]["role"] = "ignore"
    assert config_hash(DatasetConfig.model_validate(payload)) != config_hash(synthetic_config)
    payload = synthetic_config.model_dump(mode="json")
    payload["aggregation"] = "last"
    assert config_hash(DatasetConfig.model_validate(payload)) != config_hash(synthetic_config)


@pytest.mark.parametrize("change", ["mtime", "size", "config", "missing_frame", "bad_meta"])
def test_cache_expiration(synthetic_config: DatasetConfig, tmp_path: Path, change: str) -> None:
    root = tmp_path / "cache"
    write_cache(synthetic_config, prepare(synthetic_config), root)
    cfg = synthetic_config
    match change:
        case "mtime":
            stat = cfg.source.path.stat()
            os.utime(cfg.source.path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
        case "size":
            with cfg.source.path.open("a", encoding="utf-8") as stream:
                stream.write("\n")
        case "config":
            cfg = cfg.model_copy(update={"aggregation": "last"})
        case "missing_frame":
            (cache_dir(cfg, root) / "frame.parquet").unlink()
        case "bad_meta":
            (cache_dir(cfg, root) / "meta.json").write_text("{broken", encoding="utf-8")
    assert not is_fresh(cfg, root)
    with pytest.raises(DatasetNotIngested):
        read_cache(cfg, root)
