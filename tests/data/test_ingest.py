import importlib
import os
from pathlib import Path

import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.data.cache import cache_dir, is_fresh
from tsllm.data.prepare import ingest_dataset
from tsllm.data.registry import DatasetConfigError
from tsllm.data.types import PreparedFrame
from tsllm.reporting import NullReporter, Reporter


class RecordingReporter(NullReporter):
    def __init__(self) -> None:
        self.stages: list[str] = []

    def stage(self, name: str) -> None:
        self.stages.append(name)


def test_ingest_reuses_cache_and_force_rebuilds(
    synthetic_config: DatasetConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("tsllm.data.prepare")
    original = module.prepare
    calls = 0

    def counted(cfg: DatasetConfig, reporter: Reporter | None = None) -> PreparedFrame:
        nonlocal calls
        calls += 1
        return original(cfg, reporter)

    monkeypatch.setattr(module, "prepare", counted)
    root = tmp_path / "cache"
    reporter = RecordingReporter()
    first = ingest_dataset(synthetic_config, reporter, cache_root=root)
    assert reporter.stages == ["read", "resample", "segment", "split", "write", "done"]
    assert calls == 1 and is_fresh(synthetic_config, root)
    second = ingest_dataset(synthetic_config, reporter, cache_root=root)
    assert calls == 1 and second.frame.equals(first.frame)
    third = ingest_dataset(synthetic_config, reporter, force=True, cache_root=root)
    assert calls == 2 and third.frame.equals(first.frame)


@pytest.mark.parametrize("phase", ["prepare", "write_cache", "after_write_cache"])
def test_source_changes_cannot_produce_fresh_cache(
    synthetic_config: DatasetConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    module = importlib.import_module("tsllm.data.prepare")
    root = tmp_path / "cache"
    original = getattr(module, "prepare" if phase == "prepare" else "write_cache")

    def change_source() -> None:
        source = synthetic_config.source.path
        stat = source.stat()
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))

    if phase == "prepare":

        def changed_prepare(cfg: DatasetConfig, reporter: Reporter | None = None) -> PreparedFrame:
            result = original(cfg, reporter)
            change_source()
            return result

        monkeypatch.setattr(module, phase, changed_prepare)
    else:

        def changed_write(
            cfg: DatasetConfig, prepared: PreparedFrame, root: Path | None = None
        ) -> PreparedFrame:
            if phase == "write_cache":
                change_source()
            result = original(cfg, prepared, root)
            if phase == "after_write_cache":
                change_source()
            return result

        monkeypatch.setattr(module, "write_cache", changed_write)
    with pytest.raises(DatasetConfigError, match="source changed"):
        ingest_dataset(synthetic_config, NullReporter(), cache_root=root)
    assert not is_fresh(synthetic_config, root)
    assert not (cache_dir(synthetic_config, root) / "meta.json").exists()


def test_missing_source_is_a_domain_error(synthetic_config: DatasetConfig, tmp_path: Path) -> None:
    synthetic_config.source.path.unlink()
    with pytest.raises(DatasetConfigError, match="cannot be accessed"):
        ingest_dataset(synthetic_config, NullReporter(), cache_root=tmp_path / "cache")
