from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from tsllm.cli import app
from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import dump_yaml
from tsllm.data.cache import cache_dir, config_hash, read_cache

runner = CliRunner()


def register(cfg: DatasetConfig, root: Path) -> None:
    directory = root / "configs" / "datasets"
    directory.mkdir(parents=True, exist_ok=True)
    dump_yaml(cfg, directory / f"{cfg.id}.yaml")


def test_cli_help_and_empty_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["--help"]).exit_code == 0
    help_result = runner.invoke(app, ["data", "--help"])
    assert help_result.exit_code == 0
    assert all(command in help_result.output for command in ["list", "ingest", "profile"])
    empty = runner.invoke(app, ["data", "list"])
    assert empty.exit_code == 0 and "No datasets registered" in empty.output


def test_cli_ingest_list_profile_and_force(
    synthetic_config: DatasetConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    register(synthetic_config, tmp_path)
    initial = runner.invoke(app, ["data", "list"])
    assert initial.exit_code == 0 and "missing_or_stale" in initial.output
    assert config_hash(synthetic_config) in initial.output
    result = runner.invoke(app, ["data", "ingest", "synthetic"])
    assert result.exit_code == 0, result.output
    assert "[write]" in result.output and "elapsed_seconds=" in result.output
    assert (cache_dir(synthetic_config) / "frame.parquet").is_file()
    assert "ready" in runner.invoke(app, ["data", "list"]).output
    meta = read_cache(synthetic_config).meta
    profile = runner.invoke(app, ["data", "profile", "synthetic"])
    assert profile.exit_code == 0, profile.output
    assert f"eligible_points={meta['eligible_points']}" in profile.output
    assert f"segments={meta['segment_count']}" in profile.output
    assert all(boundary in profile.output for boundary in meta["split_boundaries"].values())
    assert "null_rate=" in profile.output
    assert not any(
        name in profile.output for name in ["eligible_mean", "eligible_min", "eligible_max"]
    )
    reused = runner.invoke(app, ["data", "ingest", "synthetic"])
    assert reused.exit_code == 0 and "reused its current cache" in reused.output
    assert "[read]" not in reused.output
    forced = runner.invoke(app, ["data", "ingest", "synthetic", "--force"])
    assert forced.exit_code == 0 and "[read]" in forced.output


def test_profile_never_ingests_missing_or_stale_cache(
    synthetic_config: DatasetConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    register(synthetic_config, tmp_path)
    result = runner.invoke(app, ["data", "profile", "synthetic"])
    assert result.exit_code == 1 and "DATASET_NOT_INGESTED" in result.output
    assert not cache_dir(synthetic_config).exists()
    assert runner.invoke(app, ["data", "ingest", "synthetic"]).exit_code == 0
    with synthetic_config.source.path.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    result = runner.invoke(app, ["data", "profile", "synthetic"])
    assert result.exit_code == 1 and "DATASET_NOT_INGESTED" in result.output
    assert "[read]" not in result.output


def test_cli_errors_are_sanitized(
    config_factory: Callable[..., DatasetConfig], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = config_factory(channels=[{"name": "x"}])
    register(cfg, tmp_path)
    sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
    pl.DataFrame({"date": [datetime(2024, 1, 1)], "x": [sentinel]}).write_csv(cfg.source.path)
    result = runner.invoke(app, ["data", "ingest", "synthetic"])
    assert result.exit_code == 1 and "DATASET_CONFIG_INVALID" in result.output
    assert sentinel not in result.output and "Traceback" not in result.output
    missing = runner.invoke(app, ["data", "ingest", "unknown"])
    assert missing.exit_code == 1 and "DATASET_NOT_FOUND" in missing.output
