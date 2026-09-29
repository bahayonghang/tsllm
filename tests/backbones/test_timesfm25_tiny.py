"""Real random TimesFM configuration; no model downloads or GPU."""

from pathlib import Path

import numpy as np
import pytest

from tsllm.backbones import get_backbone
from tsllm.backbones.base import CapabilityError
from tsllm.config.backbone import BackboneConfig, FinetuneConfig, LoraSpec
from tsllm.data.types import SegmentSet

from .conftest import RecordingReporter, context


@pytest.fixture
def tiny_timesfm(tmp_path: Path) -> Path:
    import torch
    from transformers import TimesFm2_5Config, TimesFm2_5ModelForPrediction

    torch.manual_seed(0)
    torch.set_num_threads(1)
    config = TimesFm2_5Config(
        patch_length=8,
        context_length=32,
        horizon_length=8,
        num_hidden_layers=1,
        hidden_size=32,
        intermediate_size=32,
        head_dim=16,
        num_attention_heads=2,
        num_key_value_heads=2,
        output_quantile_len=8,
        max_position_embeddings=32,
    )
    path = tmp_path / "base"
    TimesFm2_5ModelForPrediction(config).save_pretrained(path)
    return path


def test_timesfm_shape_nan_and_non_patch_context(
    tiny_timesfm: Path,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    model = get_backbone("timesfm25")
    model.load(
        BackboneConfig(name="timesfm25", checkpoint=str(tiny_timesfm), device="cpu"),
        None,
        reporter=reporter,
    )
    values = sine_segments.arrays[0][None, :, :30].copy()
    values[..., :2] = np.nan
    values[..., 8] = np.nan
    values[..., -1] = np.nan
    original = values.copy()
    output = model.forecast(context(values), 8)
    assert output.mean.shape == (1, 2, 8)
    assert output.quantiles is not None and output.quantiles.shape == (1, 2, 8, 9)
    assert np.isfinite(output.mean).all()
    assert np.isfinite(output.quantiles).all()
    assert model.embed(context(values)).shape == (1, 64)
    np.testing.assert_equal(values, original)
    values[:, 0] = np.nan
    output = model.forecast(context(values), 8)
    assert np.isnan(output.mean[:, 0]).all()
    assert np.isfinite(output.mean[:, 1]).all()
    with pytest.raises(CapabilityError):
        model.forecast(context(values), 9)


def test_timesfm_loss_decreases_and_roundtrip(
    tiny_timesfm: Path,
    tmp_path: Path,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    config = BackboneConfig(name="timesfm25", checkpoint=str(tiny_timesfm), device="cpu")
    model = get_backbone("timesfm25")
    model.load(config, None, reporter=reporter)
    finetune = FinetuneConfig(
        num_steps=20,
        batch_size=8,
        learning_rate=0.01,
        eval_every=5,
        lora=LoraSpec(r=2, alpha=4, dropout=0),
    )
    with pytest.raises(CapabilityError, match="full"):
        model.finetune(sine_segments, None, finetune, 30, 8, reporter, mode="full")
    model.finetune(sine_segments, sine_segments, finetune, 30, 8, reporter, mode="lora")
    losses = [v for name, v, _ in reporter.metrics if name == "train_loss"]
    print(f"timesfm25 train_loss_first={losses[0]:.8f} train_loss_step20={losses[-1]:.8f}")
    assert len(losses) == 20
    assert losses[-1] < losses[0]
    assert len([v for name, v, _ in reporter.metrics if name == "val_loss"]) == 4
    batch = context(sine_segments.arrays[0][None, :, :30])
    expected = model.forecast(batch, 8).mean
    saved = tmp_path / "adapter"
    model.save_adapter(saved)
    restored = get_backbone("timesfm25")
    restored.load(config, None, reporter=reporter)
    restored.load_adapter(saved)
    np.testing.assert_allclose(restored.forecast(batch, 8).mean, expected, rtol=1e-6, atol=1e-6)


def test_timesfm_training_drops_missing_targets(
    tiny_timesfm: Path,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    model = get_backbone("timesfm25")
    model.load(
        BackboneConfig(name="timesfm25", checkpoint=str(tiny_timesfm), device="cpu"),
        None,
        reporter=reporter,
    )
    values = sine_segments.arrays[0][:, :40].copy()
    values[0, 32:] = np.nan
    train = SegmentSet([values], sine_segments.channel_names, sine_segments.freq)
    model.finetune(
        train,
        None,
        FinetuneConfig(num_steps=1, batch_size=8),
        32,
        8,
        reporter,
        mode="lora",
    )
    assert np.isfinite([v for n, v, _ in reporter.metrics if n == "train_loss"]).all()
    reporter.steps.clear()
    values[1, 32:] = np.nan
    with pytest.raises(ValueError, match="complete target"):
        model.finetune(
            train,
            None,
            FinetuneConfig(num_steps=1, batch_size=8),
            32,
            8,
            reporter,
            mode="lora",
        )
    assert not reporter.steps
