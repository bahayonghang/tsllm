"""Explicit real-checkpoint acceptance. Missing weights and hardware are failures."""

import gc
import json
import os
from time import perf_counter
from typing import Any

import numpy as np
import pytest

from tsllm.backbones import get_backbone
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.data.stats import ChannelStats, FitStats
from tsllm.data.types import SegmentSet

from .conftest import RecordingReporter, context

pytestmark = pytest.mark.weights


def acceptance_config(name: str, *, dtype: str = "fp32") -> BackboneConfig:
    return BackboneConfig.model_validate(
        {
            "name": name,
            "device": "cuda",
            "dtype": dtype,
            "checkpoint": os.environ.get(f"TSLLM_{name.upper()}_CHECKPOINT"),
            "revision": os.environ.get(f"TSLLM_{name.upper()}_REVISION"),
        }
    )


def acceptance_inputs(length: int) -> tuple[SegmentSet, FitStats]:
    times = np.arange(3 * length + 64, dtype=np.float32)
    values = np.stack([np.sin(times * 2 * np.pi / 32), np.cos(times * 2 * np.pi / 32)])
    channels = ["channel_0", "channel_1"]
    return (
        SegmentSet([values], channels, "1min"),
        FitStats({name: ChannelStats(len(times), 0.0, 1.0, {}) for name in channels}),
    )


@pytest.mark.parametrize(
    "name,length,mode",
    [
        ("chronos2", 128, "lora"),
        ("timesfm25", 128, "lora"),
        ("ttm", 512, "head"),
    ],
)
def test_real_checkpoint_five_steps(name: str, length: int, mode: Any) -> None:
    import torch

    assert torch.cuda.is_available()
    torch.manual_seed(0)
    torch.cuda.reset_peak_memory_stats()
    reporter = RecordingReporter()
    train, stats = acceptance_inputs(length)
    model: Any = get_backbone(name)
    record: dict[str, Any] = {
        "backbone": name,
        "mode": mode,
        "dtype": "fp32",
        "device": "cuda",
        "steps": 5,
        "status": "failed",
    }
    started = perf_counter()
    try:
        model.load(acceptance_config(name), stats, reporter=reporter)
        record["load_call_seconds"] = perf_counter() - started
        forecast_started = perf_counter()
        prediction = model.forecast(context(train.arrays[0][None, :, :length]), 16)
        torch.cuda.synchronize()
        record["initial_forecast_seconds"] = perf_counter() - forecast_started
        record["load_and_forecast_seconds"] = perf_counter() - started
        pipeline = getattr(model, "pipeline", None)
        underlying = pipeline.model if pipeline is not None else model.model
        parameter = next(underlying.parameters())
        record["parameter_device"], record["parameter_dtype"] = (
            str(parameter.device),
            str(parameter.dtype),
        )
        assert parameter.device.type == "cuda" and parameter.dtype == torch.float32
        assert prediction.mean.shape == (1, 2, 16) and np.isfinite(prediction.mean).all()
        assert model.resolved_checkpoint is not None
        record["resolved_revision"] = model.resolved_checkpoint.revision
        record["checkpoint_source"] = model.resolved_checkpoint.source
        fit_started = perf_counter()
        model.finetune(
            train, None, FinetuneConfig(num_steps=5, batch_size=2), length, 16, reporter, mode=mode
        )
        torch.cuda.synchronize()
        record["train_seconds"] = perf_counter() - fit_started
        trainable = next(v for n, v, _ in reporter.metrics if n == "trainable_params")
        total = next(v for n, v, _ in reporter.metrics if n == "total_params")
        record.update(
            trainable_params=trainable, total_params=total, trainable_fraction=trainable / total
        )
        if mode == "lora":
            assert 0 < trainable < total * 0.05
        else:
            assert 0 < trainable < total
        record["observed_steps"] = [step for step, _ in reporter.steps]
        assert reporter.steps == [(step, 5) for step in range(1, 6)]
        losses = [value for metric, value, _ in reporter.metrics if metric == "train_loss"]
        assert len(losses) == 5 and np.isfinite(losses).all()
        record["train_losses"] = losses
        record["train_loss_first"], record["train_loss_step5"] = losses[0], losses[-1]
        result = model.forecast(context(train.arrays[0][None, :, :length]), 16)
        assert np.isfinite(result.mean).all()
        record["status"] = "passed"
    finally:
        record["total_seconds"] = perf_counter() - started
        record["peak_vram_mib"] = torch.cuda.max_memory_allocated() / 1024**2
        print(json.dumps(record, sort_keys=True))
        del model
        gc.collect()
        torch.cuda.empty_cache()
