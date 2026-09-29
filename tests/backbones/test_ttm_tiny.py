"""Real random TTM, head training, and checkpoint-selection regressions."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tsllm.backbones import get_backbone
from tsllm.backbones.base import BackboneLoadError, CapabilityError
from tsllm.backbones.checkpoint import ResolvedCheckpoint
from tsllm.backbones.ttm import TtmBackbone
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.data.stats import ChannelStats, FitStats
from tsllm.data.types import SegmentSet

from .conftest import RecordingReporter, context


@pytest.fixture
def tiny_ttm(tmp_path: Path) -> Path:
    import torch
    from tsfm_public.models.tinytimemixer import TinyTimeMixerConfig, TinyTimeMixerForPrediction

    torch.manual_seed(0)
    torch.set_num_threads(1)
    config = TinyTimeMixerConfig(
        context_length=32,
        prediction_length=8,
        num_input_channels=2,
        patch_length=8,
        patch_stride=8,
        d_model=16,
        num_layers=1,
        decoder_num_layers=1,
        decoder_d_model=16,
        dropout=0,
        head_dropout=0,
        adaptive_patching_levels=0,
        decoder_adaptive_patching_levels=0,
    )
    path = tmp_path / "base"
    TinyTimeMixerForPrediction(config).save_pretrained(path)
    return path


@pytest.fixture
def tiny_ttm_prefix(tiny_ttm: Path, tmp_path: Path) -> Path:
    from tsfm_public.models.tinytimemixer import TinyTimeMixerConfig, TinyTimeMixerForPrediction

    config = TinyTimeMixerConfig.from_pretrained(
        tiny_ttm,
        resolution_prefix_tuning=True,
        frequency_token_vocab_size=10,
        num_patches=None,
        local_files_only=True,
    )
    path = tmp_path / "prefix-base"
    TinyTimeMixerForPrediction(config).save_pretrained(path)
    return path


@pytest.mark.parametrize("freq,token", [("1min", 1), ("5min", 3), ("10s", 0)])
def test_ttm_prefix_frequency_forecast_and_head(
    tiny_ttm_prefix: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
    freq: str,
    token: int,
) -> None:
    import torch

    model = TtmBackbone()
    model.load(
        BackboneConfig(name="ttm", checkpoint=str(tiny_ttm_prefix), device="cpu"),
        unit_stats,
        reporter=reporter,
    )
    model._ensure_model(32, 8, sine_segments.channel_names)
    observed: list[list[int]] = []

    def capture(module: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        actual = kwargs.get("freq_token")
        assert actual is not None and actual.dtype == torch.long
        assert actual.device == kwargs["past_values"].device
        assert actual.shape == (len(kwargs["past_values"]),)
        observed.append(actual.tolist())

    hook = model.model.register_forward_pre_hook(capture, with_kwargs=True)
    batch = replace(context(sine_segments.arrays[0][None, :, :32]), freq=freq)
    assert np.isfinite(model.forecast(batch, 8).mean).all()
    segments = replace(sine_segments, freq=freq)
    model.finetune(
        segments,
        segments,
        FinetuneConfig(num_steps=2, batch_size=2, eval_every=1),
        32,
        8,
        reporter,
        mode="head",
    )
    hook.remove()
    assert observed == [[token], [token, token], [token, token], [token, token], [token, token]]
    assert reporter.steps == [(1, 2), (2, 2)]
    assert len([value for name, value, _ in reporter.metrics if name == "val_loss"]) == 2
    warnings = [message for message, level in reporter.logs if level == "warning"]
    assert any("OOV" in message for message in warnings) == (token == 0)


def test_ttm_prefix_frequency_rejects_invalid_inputs(
    tiny_ttm_prefix: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    import torch

    model = TtmBackbone()
    model.load(
        BackboneConfig(name="ttm", checkpoint=str(tiny_ttm_prefix), device="cpu"),
        unit_stats,
        reporter=reporter,
    )
    batch = context(sine_segments.arrays[0][None, :, :32])
    with pytest.raises(ValueError, match="invalid TTM frequency"):
        model.forecast(replace(batch, freq="bogus"), 8)
    model.model.config.frequency_token_vocab_size = 2
    with pytest.raises(CapabilityError, match="vocabulary"):
        model.forecast(replace(batch, freq="5min"), 8)
    original = {name: value.detach().clone() for name, value in model.model.named_parameters()}
    with pytest.raises(ValueError, match="frequency differs"):
        model.finetune(
            sine_segments,
            replace(sine_segments, freq="5min"),
            FinetuneConfig(num_steps=1),
            32,
            8,
            reporter,
            mode="head",
        )
    assert not reporter.steps
    for name, value in model.model.named_parameters():
        torch.testing.assert_close(value, original[name], rtol=0, atol=0)


def test_ttm_nan_native_context_and_local_revision(
    tiny_ttm: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    model = get_backbone("ttm")
    model.load(
        BackboneConfig(name="ttm", checkpoint=str(tiny_ttm), device="cpu"),
        unit_stats,
        reporter=reporter,
    )
    assert model.resolved_checkpoint is None
    values = sine_segments.arrays[0][None, :, :40].copy()
    values[:, 0, :] = np.nan
    values[:, 1, [0, 4, 39]] = np.nan
    output = model.forecast(context(values), 8)
    assert output.mean.shape == (1, 2, 8)
    assert np.isfinite(output.mean).all()
    assert model.resolved_checkpoint is not None and model.resolved_checkpoint.revision is None
    assert any("requested context 40; native context 32" in m for m, _ in reporter.logs)
    assert np.isfinite(model.forecast(context(values[..., :24]), 4).mean).all()
    with pytest.raises(BackboneLoadError, match="H <= 8"):
        model.forecast(context(values), 9)


def test_ttm_head_loss_decreases_and_roundtrip(
    tiny_ttm: Path,
    tmp_path: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    import torch

    config = BackboneConfig(name="ttm", checkpoint=str(tiny_ttm), device="cpu")
    model = get_backbone("ttm")
    assert isinstance(model, TtmBackbone)
    model.load(config, unit_stats, reporter=reporter)
    batch = context(sine_segments.arrays[0][None, :, :32])
    model.forecast(batch, 8)
    original = {n: p.detach().clone() for n, p in model.model.backbone.named_parameters()}
    finetune = FinetuneConfig(num_steps=20, batch_size=8, learning_rate=0.01, eval_every=5)
    with pytest.raises(CapabilityError, match="lora"):
        model.finetune(sine_segments, None, finetune, 32, 8, reporter, mode="lora")
    model.finetune(sine_segments, sine_segments, finetune, 32, 8, reporter, mode="head")
    losses = [v for name, v, _ in reporter.metrics if name == "train_loss"]
    print(f"ttm train_loss_first={losses[0]:.8f} train_loss_step20={losses[-1]:.8f}")
    assert len(losses) == 20 and losses[-1] < losses[0]
    for name, parameter in model.model.backbone.named_parameters():
        assert not parameter.requires_grad
        torch.testing.assert_close(parameter, original[name], rtol=0, atol=0)
    assert any(p.requires_grad for p in model.model.decoder.parameters())
    expected = model.forecast(batch, 8).mean
    saved = tmp_path / "head"
    model.save_adapter(saved)
    restored = get_backbone("ttm")
    restored.load(config, unit_stats, reporter=reporter)
    restored.load_adapter(saved)
    np.testing.assert_allclose(restored.forecast(batch, 8).mean, expected, rtol=1e-6, atol=1e-6)


def test_ttm_explicit_revision_bypasses_selector(
    monkeypatch: pytest.MonkeyPatch,
    tiny_ttm: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    from tsllm.backbones import ttm

    calls: list[str | None] = []

    def resolve(cfg: BackboneConfig) -> ResolvedCheckpoint:
        calls.append(cfg.revision)
        return ResolvedCheckpoint(tiny_ttm, "resolved-commit", "huggingface")

    monkeypatch.setattr(ttm, "resolve_checkpoint", resolve)
    model = get_backbone("ttm")
    model.load(
        BackboneConfig(name="ttm", checkpoint="custom/model", revision="user-branch", device="cpu"),
        unit_stats,
        reporter=reporter,
    )
    assert np.isfinite(model.forecast(context(sine_segments.arrays[0][None, :, :32]), 8).mean).all()
    assert calls == ["user-branch"]
    assert (
        model.resolved_checkpoint is not None
        and model.resolved_checkpoint.revision == "resolved-commit"
    )


def test_ttm_hf_key_maps_to_branch(
    monkeypatch: pytest.MonkeyPatch,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    from tsllm.backbones import ttm

    calls = []

    def stop_before_download(cfg: BackboneConfig) -> ResolvedCheckpoint:
        calls.append(cfg.revision)
        raise BackboneLoadError("test stops before download")

    monkeypatch.setattr(ttm, "resolve_checkpoint", stop_before_download)
    model = get_backbone("ttm")
    model.load(BackboneConfig(name="ttm", device="cpu"), unit_stats, reporter=reporter)
    with pytest.raises(BackboneLoadError, match="stops before download"):
        model.forecast(context(np.ones((1, 2, 512))), 96)
    assert calls == ["main"]
    with pytest.raises(BackboneLoadError, match="available L/H"):
        model.forecast(context(np.ones((1, 2, 32))), 8)


def test_ttm_save_preserves_loaded_selection_dimensions(
    tiny_ttm: Path,
    tmp_path: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    model = get_backbone("ttm")
    model.load(
        BackboneConfig(name="ttm", checkpoint=str(tiny_ttm), device="cpu"),
        unit_stats,
        reporter=reporter,
    )
    model.finetune(
        sine_segments,
        None,
        FinetuneConfig(num_steps=1, batch_size=2),
        32,
        8,
        reporter,
        mode="head",
    )
    model.forecast(context(sine_segments.arrays[0][None, :, :24]), 4)
    path = tmp_path / "head"
    model.save_adapter(path)
    saved = json.loads((path / "head.json").read_text(encoding="utf-8"))
    assert (saved["context_length"], saved["horizon"]) == (32, 8)
    restored = get_backbone("ttm")
    restored.load(
        BackboneConfig(name="ttm", checkpoint=str(tiny_ttm), device="cpu"),
        unit_stats,
        reporter=reporter,
    )
    restored.load_adapter(path)
    batch = context(sine_segments.arrays[0][None, :, :24])
    np.testing.assert_allclose(
        restored.forecast(batch, 4).mean,
        model.forecast(batch, 4).mean,
        rtol=1e-6,
        atol=1e-6,
    )
    saved["resolved_revision"] = "different-base-revision"
    (path / "head.json").write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(BackboneLoadError, match="revision differs"):
        restored.load_adapter(path)


def test_ttm_scaling_by_channel_and_partial_targets(
    tiny_ttm: Path,
    sine_segments: SegmentSet,
    unit_stats: FitStats,
    reporter: RecordingReporter,
) -> None:
    cfg = BackboneConfig(name="ttm", checkpoint=str(tiny_ttm), device="cpu")
    normalized = get_backbone("ttm")
    normalized.load(cfg, unit_stats, reporter=reporter)
    values = sine_segments.arrays[0][None, :, :32]
    expected = normalized.forecast(context(values), 8).mean
    means = np.array([10, -20], dtype=np.float32)[None, :, None]
    scales = np.array([2, 4], dtype=np.float32)[None, :, None]
    stats = FitStats(
        {
            "channel_1": ChannelStats(320, -20, 4, {}),
            "channel_0": ChannelStats(320, 10, 2, {}),
        }
    )
    physical = get_backbone("ttm")
    physical.load(cfg, stats, reporter=reporter)
    prediction = physical.forecast(context(values * scales + means), 8).mean
    np.testing.assert_allclose(prediction, expected * scales + means, rtol=1e-6, atol=1e-6)
    training = sine_segments.arrays[0][:, :40].copy()
    training[:, 32:36] = np.nan
    train = SegmentSet([training], sine_segments.channel_names, sine_segments.freq)
    normalized.finetune(
        train,
        None,
        FinetuneConfig(num_steps=1, batch_size=2),
        32,
        8,
        reporter,
        mode="head",
    )
    assert np.isfinite([v for n, v, _ in reporter.metrics if n == "train_loss"]).all()
    reporter.steps.clear()
    training[:, 32:] = np.nan
    with pytest.raises(ValueError, match="no observed targets"):
        normalized.finetune(
            train,
            None,
            FinetuneConfig(num_steps=1, batch_size=2),
            32,
            8,
            reporter,
            mode="head",
        )
    assert not reporter.steps
