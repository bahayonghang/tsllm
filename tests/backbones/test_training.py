"""Training-loop boundaries and validation model selection."""

from typing import Any

import numpy as np
import pytest

from tsllm.backbones.training import train_model
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.data.types import SegmentSet

from .conftest import RecordingReporter


def test_training_rejects_validation_channel_order(
    sine_segments: SegmentSet, reporter: RecordingReporter
) -> None:
    import torch

    model = torch.nn.Linear(1, 1, bias=False)
    before = model.weight.detach().clone()
    validation = SegmentSet(
        [sine_segments.arrays[0][::-1].copy()],
        sine_segments.channel_names[::-1],
        sine_segments.freq,
    )
    with pytest.raises(ValueError, match="channel order"):
        train_model(
            model,
            sine_segments,
            validation,
            FinetuneConfig(num_steps=1, batch_size=2),
            BackboneConfig(name="ttm", device="cpu"),
            8,
            2,
            reporter,
            lambda x, y: model.weight.square().mean(),
        )
    torch.testing.assert_close(model.weight, before, rtol=0, atol=0)
    assert not reporter.steps


def test_training_reuses_validation_windows_and_restores_best(
    sine_segments: SegmentSet, reporter: RecordingReporter
) -> None:
    import torch

    model = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(0)
    validation_windows: list[np.ndarray] = []
    best: list[Any] = []

    def loss(x: np.ndarray, y: np.ndarray) -> Any:
        if model.training:
            return (model.weight - 1).square().mean()
        validation_windows.append(x.copy())
        if not best:
            best.append(model.weight.detach().clone())
        return model.weight.square().mean()

    train_model(
        model,
        sine_segments,
        sine_segments,
        FinetuneConfig(num_steps=3, batch_size=2, learning_rate=0.1, eval_every=1),
        BackboneConfig(name="ttm", device="cpu"),
        8,
        2,
        reporter,
        loss,
    )
    assert len(validation_windows) == 3
    for values in validation_windows[1:]:
        np.testing.assert_array_equal(values, validation_windows[0])
    losses = [value for name, value, _ in reporter.metrics if name == "val_loss"]
    assert losses[0] < losses[-1]
    torch.testing.assert_close(model.weight, best[0], rtol=0, atol=0)
    assert not model.training
