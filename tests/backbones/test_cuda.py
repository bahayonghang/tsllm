"""Explicit CUDA and bf16 acceptance with real checkpoints."""

import gc
import json
from time import perf_counter
from typing import Any

import numpy as np
import pytest

from tsllm.backbones import get_backbone

from .conftest import RecordingReporter, context
from .test_smoke_weights import acceptance_config, acceptance_inputs

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize("name", ["chronos2", "timesfm25"])
def test_cuda_bf16_zero_shot(name: str) -> None:
    import torch

    assert torch.cuda.is_available()
    assert torch.cuda.get_device_capability() == (12, 0)
    assert torch.cuda.is_bf16_supported()
    torch.cuda.reset_peak_memory_stats()
    model: Any = get_backbone(name)
    train, stats = acceptance_inputs(128)
    started = perf_counter()
    record: dict[str, Any] = {
        "backbone": name,
        "mode": "zero_shot",
        "dtype": "bf16",
        "device": "cuda",
        "status": "failed",
    }
    try:
        model.load(acceptance_config(name, dtype="bf16"), stats, reporter=RecordingReporter())
        record["load_call_seconds"] = perf_counter() - started
        forecast_started = perf_counter()
        result = model.forecast(context(train.arrays[0][None, :, :128]), 16)
        torch.cuda.synchronize()
        record["forecast_seconds"] = perf_counter() - forecast_started
        underlying = model.pipeline.model if name == "chronos2" else model.model
        assert next(underlying.parameters()).dtype == torch.bfloat16
        assert next(underlying.parameters()).device.type == "cuda"
        record["parameter_device"] = str(next(underlying.parameters()).device)
        record["parameter_dtype"] = str(next(underlying.parameters()).dtype)
        assert result.mean.shape == (1, 2, 16) and np.isfinite(result.mean).all()
        record["resolved_revision"] = model.resolved_checkpoint.revision
        record["status"] = "passed"
    finally:
        record["load_and_forecast_seconds"] = perf_counter() - started
        record["peak_vram_mib"] = torch.cuda.max_memory_allocated() / 1024**2
        print(json.dumps(record, sort_keys=True))
        del model
        gc.collect()
        torch.cuda.empty_cache()
