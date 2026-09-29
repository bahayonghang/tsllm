"""Numerical baseline behavior, NaN policy, and training boundaries."""

from pathlib import Path

import numpy as np
import pytest

from tsllm.backbones import get_backbone
from tsllm.backbones.base import CapabilityError
from tsllm.backbones.nan import ffill_bfill, interpolate_1d
from tsllm.backbones.windows import sample_training_windows
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.data.stats import ChannelStats, FitStats
from tsllm.data.types import SegmentSet

from .conftest import RecordingReporter, context


def test_persistence_nan(reporter: RecordingReporter) -> None:
    model = get_backbone("persistence")
    model.load(BackboneConfig(name="persistence"), None, reporter=reporter)
    batch = context(np.array([[[1, np.nan, 3, np.nan], [np.nan] * 4]]))
    result = model.forecast(batch, 3)
    np.testing.assert_equal(result.mean, [[[3, 3, 3], [np.nan] * 3]])
    assert result.quantiles is None
    with pytest.raises(CapabilityError):
        model.embed(batch)


def test_features_nan_and_order(reporter: RecordingReporter) -> None:
    model = get_backbone("features")
    model.load(BackboneConfig(name="features"), None, reporter=reporter)
    values = np.array([[[1, np.nan, 5, 7], [np.nan] * 4]])
    result = model.embed(context(values))
    expected = [13 / 3, np.std([1, 5, 7]), 7, 2, 1, 7] + [0] * 6
    np.testing.assert_allclose(result, [expected], rtol=1e-6)
    assert reporter.logs == [("all-NaN context channels: 1", "warning")]


def test_nan_tools() -> None:
    row = np.array([np.nan, 1, np.nan, 3, np.nan], dtype=np.float32)
    np.testing.assert_equal(interpolate_1d(row), [1, 2, 3, 3])
    np.testing.assert_equal(ffill_bfill(row[None]), [[1, 1, 1, 3, 3]])
    assert interpolate_1d(np.full(4, np.nan, dtype=np.float32)).size == 0
    np.testing.assert_equal(ffill_bfill(np.full((1, 4), np.nan, dtype=np.float32)), [[0] * 4])


def test_windows_never_cross_arrays() -> None:
    segments = SegmentSet(
        [np.arange(20, dtype=np.float32)[None], np.arange(1000, 1030, dtype=np.float32)[None]],
        ["x"],
        "1min",
    )
    x, y = sample_training_windows(segments, 5, 4, 100, np.random.default_rng(7))
    repeated = sample_training_windows(segments, 5, 4, 100, np.random.default_rng(7))
    np.testing.assert_equal(x, repeated[0])
    np.testing.assert_equal(y, repeated[1])
    joined = np.concatenate([x, y], axis=-1)
    np.testing.assert_equal(np.diff(joined, axis=-1), np.ones((100, 1, 8)))
    assert ((joined < 20).all(axis=(1, 2)) | (joined >= 1000).all(axis=(1, 2))).all()
    with pytest.raises(ValueError, match="long enough"):
        sample_training_windows(segments, 30, 1, 1, np.random.default_rng(0))


def test_ridge_numeric_nan_and_roundtrip(tmp_path: Path, reporter: RecordingReporter) -> None:
    data = np.arange(120, dtype=np.float32)[None]
    train = SegmentSet([data], ["channel_0"], "1min")
    stats = FitStats({"channel_0": ChannelStats(120, 60, 35, {})})
    cfg = BackboneConfig(name="ridge", options={"alpha": 0.00001, "max_samples": 256})
    model = get_backbone("ridge")
    model.load(cfg, stats, reporter=reporter)
    with pytest.raises(CapabilityError, match="lora"):
        model.finetune(train, None, FinetuneConfig(), 8, 3, reporter, mode="lora")
    model.finetune(train, None, FinetuneConfig(), 8, 3, reporter, mode="full")
    batch = context(np.arange(40, 48, dtype=np.float32)[None, None])
    result = model.forecast(batch, 3).mean
    np.testing.assert_allclose(result, [[[48, 49, 50]]], rtol=1e-5)
    missing = batch.values.copy()
    missing[..., 3] = np.nan
    assert np.isfinite(model.forecast(context(missing), 3).mean).all()
    model.save_adapter(tmp_path)
    restored = get_backbone("ridge")
    restored.load(cfg, stats, reporter=reporter)
    restored.load_adapter(tmp_path)
    np.testing.assert_allclose(restored.forecast(batch, 3).mean, result, rtol=1e-6)
    data[:, 20:24] = np.nan
    model.finetune(train, None, FinetuneConfig(), 8, 3, reporter, mode="full")
    dropped = [v for n, v, _ in reporter.metrics if n == "dropped_target_windows"]
    assert dropped[-1] > 0
