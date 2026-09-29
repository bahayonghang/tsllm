"""Shared sampling, optimization, and validation for TimesFM and TTM."""

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from typing import Any

import numpy as np
from numpy.typing import NDArray

from tsllm.backbones.base import BackboneLoadError
from tsllm.backbones.windows import sample_training_windows
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.data.types import SegmentSet
from tsllm.reporting import Reporter


def torch_dtype(cfg: BackboneConfig) -> Any:
    import torch

    if cfg.device == "cuda" and not torch.cuda.is_available():
        raise BackboneLoadError("CUDA was requested but is unavailable")
    return torch.bfloat16 if cfg.device == "cuda" and cfg.dtype == "bf16" else torch.float32


def autocast(cfg: BackboneConfig) -> AbstractContextManager[Any]:
    import torch

    if cfg.device == "cuda" and cfg.dtype == "bf16":
        return torch.autocast("cuda", dtype=torch.bfloat16)
    return nullcontext()


def report_parameters(model: Any, reporter: Reporter) -> tuple[int, int]:
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    reporter.metric("trainable_params", float(trainable))
    reporter.metric("total_params", float(total))
    return trainable, total


def train_model(
    model: Any,
    train: SegmentSet,
    val: SegmentSet | None,
    cfg: FinetuneConfig,
    backbone_cfg: BackboneConfig,
    context_length: int,
    horizon: int,
    reporter: Reporter,
    loss_fn: Callable[[NDArray[np.float32], NDArray[np.float32]], Any],
    *,
    channel_independent: bool = False,
) -> None:
    import torch

    if val is not None and val.channel_names != train.channel_names:
        raise ValueError("training and validation channel order differs")
    rng = np.random.default_rng(0)

    def sample(segments: SegmentSet, generator: np.random.Generator) -> tuple[Any, Any]:
        x, y = sample_training_windows(segments, context_length, horizon, cfg.batch_size, generator)
        if channel_independent:
            channels = generator.integers(x.shape[1], size=len(x))
            rows = np.arange(len(x))
            x, y = x[rows, channels, None, :], y[rows, channels, None, :]
        return x, y

    validation = None if val is None else sample(val, np.random.default_rng(1))
    parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters:
        raise BackboneLoadError("fine-tuning has no trainable parameters")
    report_parameters(model, reporter)
    optimizer = torch.optim.AdamW(parameters, lr=cfg.learning_rate)
    best_loss = float("inf")
    best: dict[str, Any] | None = None
    for step in range(1, cfg.num_steps + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        with autocast(backbone_cfg):
            loss = loss_fn(*sample(train, rng))
        if loss is None or not bool(torch.isfinite(loss).all()):
            raise ValueError("training loss is not finite")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, cfg.grad_clip)
        optimizer.step()
        reporter.metric("train_loss", float(loss.detach().float().cpu()), step)
        reporter.progress(step, cfg.num_steps)
        if validation is not None and (step % cfg.eval_every == 0 or step == cfg.num_steps):
            model.eval()
            with torch.no_grad(), autocast(backbone_cfg):
                value = float(loss_fn(*validation).detach().float().cpu())
            if not np.isfinite(value):
                raise ValueError("validation loss is not finite")
            reporter.metric("val_loss", value, step)
            if value < best_loss:
                best_loss = value
                best = {
                    n: p.detach().cpu().clone()
                    for n, p in model.named_parameters()
                    if p.requires_grad
                }
    if best is not None:
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if name in best:
                    parameter.copy_(best[name].to(parameter.device))
    model.eval()
