"""Real random Chronos-2 with both training modes and offline adapter reload."""

from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from tsllm.backbones import get_backbone
from tsllm.backbones.base import BackboneLoadError, CapabilityError
from tsllm.backbones.chronos2 import Chronos2Backbone
from tsllm.config.backbone import BackboneConfig, FinetuneConfig, LoraSpec
from tsllm.data.types import SegmentSet

from .conftest import RecordingReporter, context


@pytest.fixture
def tiny_chronos(tmp_path: Path) -> Path:
    import torch
    from chronos.chronos2.config import Chronos2CoreConfig
    from chronos.chronos2.model import Chronos2Model

    torch.manual_seed(0)
    torch.set_num_threads(1)
    config = Chronos2CoreConfig(
        d_model=32,
        d_kv=8,
        d_ff=64,
        num_layers=1,
        num_heads=4,
        dropout_rate=0,
        architectures=["Chronos2Model"],
        chronos_config={
            "context_length": 32,
            "input_patch_size": 8,
            "input_patch_stride": 8,
            "output_patch_size": 8,
            "quantiles": [i / 10 for i in range(1, 10)],
            "use_reg_token": True,
            "max_output_patches": 2,
        },
    )
    path = tmp_path / "base"
    Chronos2Model(config).save_pretrained(path)
    return path


def test_chronos_shape_nan_and_embedding(
    tiny_chronos: Path,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    model = get_backbone("chronos2")
    model.load(
        BackboneConfig(
            name="chronos2",
            checkpoint=str(tiny_chronos),
            device="cpu",
            options={"quantile_levels": [0.1, 0.5, 0.9]},
        ),
        None,
        reporter=reporter,
    )
    values = np.repeat(sine_segments.arrays[0][None, :, :32], 2, axis=0)
    values[0, 0, [0, 5, 31]] = np.nan
    result = model.forecast(context(values), 8)
    assert result.mean.shape == (2, 2, 8)
    assert result.quantiles is not None and result.quantiles.shape == (2, 2, 8, 3)
    assert np.isfinite(result.mean).all()
    np.testing.assert_allclose(result.mean, result.quantiles[..., 1], rtol=1e-6)
    embeddings = model.embed(context(values))
    assert embeddings.shape == (2, 64) and np.isfinite(embeddings).all()


@pytest.mark.parametrize("mode", ["lora", "full"])
def test_chronos_modes_loss_and_roundtrip(
    mode: Any,
    tiny_chronos: Path,
    tmp_path: Path,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = BackboneConfig(name="chronos2", checkpoint=str(tiny_chronos), device="cpu")
    model = cast(Chronos2Backbone, get_backbone("chronos2"))
    model.load(config, None, reporter=reporter)
    original_pipeline = model.pipeline
    original_fit = model.pipeline.fit
    calls: list[dict[str, Any]] = []

    def observed_fit(*args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return original_fit(*args, **kwargs)

    monkeypatch.setattr(model.pipeline, "fit", observed_fit)
    finetune = FinetuneConfig(
        num_steps=20,
        batch_size=8,
        learning_rate=0.01,
        eval_every=5,
        lora=LoraSpec(r=2, alpha=4, dropout=0),
    )
    with pytest.raises(CapabilityError, match="head"):
        model.finetune(sine_segments, None, finetune, 32, 8, reporter, mode="head")
    assert not calls
    model.finetune(sine_segments, sine_segments, finetune, 32, 8, reporter, mode=mode)
    assert model.pipeline is not original_pipeline
    assert calls[0]["finetune_mode"] == mode
    assert (calls[0]["lora_config"] is None) == (mode == "full")
    assert calls[0]["inputs"] is sine_segments.arrays
    assert calls[0]["dataloader_num_workers"] == 0
    losses = [v for name, v, _ in reporter.metrics if name == "train_loss"]
    print(f"chronos2 {mode} train_loss_first={losses[0]:.8f} train_loss_step20={losses[-1]:.8f}")
    assert len(losses) == 20 and losses[-1] < losses[0]
    trainable = next(v for name, v, _ in reporter.metrics if name == "trainable_params")
    total = next(v for name, v, _ in reporter.metrics if name == "total_params")
    assert 0 < trainable <= total
    assert (trainable < total) == (mode == "lora")
    batch = context(sine_segments.arrays[0][None, :, :32])
    expected = model.forecast(batch, 8).mean
    saved = tmp_path / "adapter"
    model.save_adapter(saved)
    restored = get_backbone("chronos2")
    restored.load(config, None, reporter=reporter)
    restored.load_adapter(saved)
    np.testing.assert_allclose(restored.forecast(batch, 8).mean, expected, rtol=1e-6, atol=1e-6)


def test_chronos_missing_peft_never_uses_full(
    monkeypatch: pytest.MonkeyPatch,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    from tsllm.backbones import chronos2

    monkeypatch.setattr(chronos2, "find_spec", lambda name: None)
    model = get_backbone("chronos2")
    with pytest.raises(BackboneLoadError, match="requires peft"):
        model.finetune(sine_segments, None, FinetuneConfig(), 32, 8, reporter, mode="lora")


def test_chronos_broken_peft_never_starts_training(
    monkeypatch: pytest.MonkeyPatch,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    from tsllm.backbones import chronos2

    def unavailable(name: str) -> Any:
        raise ImportError("synthetic peft dependency failure")

    monkeypatch.setattr(chronos2, "import_module", unavailable)
    model = get_backbone("chronos2")
    with pytest.raises(BackboneLoadError, match="importable peft"):
        model.finetune(sine_segments, None, FinetuneConfig(), 32, 8, reporter, mode="lora")
    assert not reporter.steps
