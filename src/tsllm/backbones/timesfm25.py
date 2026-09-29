"""Apache-2.0 TimesFM 2.5: internal normalization and linear context gap fill.

Trailing gaps hold the last observation. All-NaN channels return NaN without a
model call. The library pads the context to a patch boundary.
"""

from importlib.util import find_spec
from pathlib import Path
from typing import Any, ClassVar, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field

from tsllm.backbones.base import (
    Backbone,
    BackboneLoadError,
    Capabilities,
    CapabilityError,
    FinetuneMode,
    ForecastOutput,
)
from tsllm.backbones.checkpoint import checkpoint_loading
from tsllm.backbones.nan import interpolate_1d
from tsllm.backbones.registry import register_backbone
from tsllm.backbones.training import autocast, torch_dtype, train_model
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.config.base import StrictModel
from tsllm.data.stats import FitStats
from tsllm.data.types import ContextBatch, SegmentSet
from tsllm.reporting import Reporter

DEFAULT_CHECKPOINT = "google/timesfm-2.5-200m-transformers"
LORA_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "fc1", "fc2"]


class TimesFm25Options(StrictModel):
    predict_batch_size: int = Field(default=512, gt=0, description="Maximum univariate batch size.")
    window_size: int | None = Field(
        default=None, gt=0, description="Optional moving-average window."
    )
    embed_channel_pool: Literal["concat", "mean"] = Field(
        default="concat", description="Concatenate or average channel embeddings."
    )


@register_backbone(
    requires=["torch", "transformers", "peft"],
    default_checkpoint=DEFAULT_CHECKPOINT,
    license="Apache-2.0",
    license_url="https://huggingface.co/google/timesfm-2.5-200m-transformers/blob/5a9806b9b291fad9233b5249d88263f1846304d3/README.md",
)
class TimesFm25Backbone(Backbone):
    name: ClassVar[str] = "timesfm25"
    Options: ClassVar[type[BaseModel]] = TimesFm25Options
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"zero_shot", "lora"},
        embed=True,
        quantiles=True,
        multivariate="channel_independent",
    )
    model: Any

    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None, *, reporter: Reporter) -> None:
        super().load(cfg, fit_stats, reporter=reporter)
        with checkpoint_loading(self.name, cfg.checkpoint or DEFAULT_CHECKPOINT):
            from transformers import TimesFm2_5ModelForPrediction

            dtype = torch_dtype(cfg)
            checkpoint = self._resolve(DEFAULT_CHECKPOINT)
            self.model = TimesFm2_5ModelForPrediction.from_pretrained(
                checkpoint.path, dtype=dtype, local_files_only=True
            )
            self.model.to(device=cfg.device)
            self.model.eval()

    def _context_length(self, length: int) -> int:
        patch = self.model.config.patch_length
        effective = ((length + patch - 1) // patch) * patch
        if effective > self.model.config.context_length:
            raise CapabilityError(
                f"timesfm25 supports context at most {self.model.config.context_length}"
            )
        return effective

    def _horizon(self, horizon: int) -> None:
        if horizon > self.model.config.horizon_length:
            raise CapabilityError(
                f"timesfm25 supports horizon at most {self.model.config.horizon_length}"
            )

    def _series(self, values: NDArray[np.float32]) -> tuple[list[int], list[Any]]:
        import torch

        indices, series = [], []
        for index, row in enumerate(values.reshape(-1, values.shape[-1])):
            clean = interpolate_1d(row)
            if len(clean):
                indices.append(index)
                series.append(
                    torch.as_tensor(clean, device=self.cfg.device, dtype=torch_dtype(self.cfg))
                )
        return indices, series

    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput:
        import torch

        self._check_batch(batch, horizon)
        self._horizon(horizon)
        length = self._context_length(batch.values.shape[-1])
        b, c, _ = batch.values.shape
        levels = list(self.model.config.quantiles)
        mean = np.full((b * c, horizon), np.nan, dtype=np.float32)
        quantiles = np.full((b * c, horizon, len(levels)), np.nan, dtype=np.float32)
        indices, series = self._series(batch.values)
        self.model.eval()
        for start in range(0, len(series), self.options.predict_batch_size):
            stop = start + self.options.predict_batch_size
            with torch.no_grad(), autocast(self.cfg):
                output = self.model(
                    past_values=series[start:stop],
                    forecast_context_len=length,
                    window_size=self.options.window_size,
                )
            mean[indices[start:stop]] = output.mean_predictions[:, :horizon].float().cpu().numpy()
            quantiles[indices[start:stop]] = (
                output.full_predictions[:, :horizon, 1:].float().cpu().numpy()
            )
        return ForecastOutput(
            mean.reshape(b, c, horizon), quantiles.reshape(b, c, horizon, -1), levels
        )

    def embed(self, batch: ContextBatch) -> NDArray[np.float32]:
        import torch

        self._check_batch(batch)
        length = self._context_length(batch.values.shape[-1])
        b, c, _ = batch.values.shape
        result = np.full((b * c, self.model.config.hidden_size), np.nan, dtype=np.float32)
        indices, series = self._series(batch.values)
        self.model.eval()
        for start in range(0, len(series), self.options.predict_batch_size):
            stop = start + self.options.predict_batch_size
            with torch.no_grad(), autocast(self.cfg):
                output = self.model(past_values=series[start:stop], forecast_context_len=length)
            result[indices[start:stop]] = output.last_hidden_state.mean(dim=1).float().cpu().numpy()
        result = result.reshape(b, c, -1)
        return (
            result.mean(axis=1)
            if self.options.embed_channel_pool == "mean"
            else result.reshape(b, -1)
        )

    def finetune(
        self,
        train: SegmentSet,
        val: SegmentSet | None,
        cfg: FinetuneConfig,
        context_length: int,
        horizon: int,
        reporter: Reporter,
        *,
        mode: FinetuneMode,
    ) -> None:
        self._check_mode(mode)
        if find_spec("peft") is None:
            raise BackboneLoadError("timesfm25 LoRA requires peft")
        import torch

        try:
            from peft import LoraConfig, get_peft_model
        except ImportError as exc:
            raise BackboneLoadError("timesfm25 LoRA requires an importable peft") from exc

        self._horizon(horizon)
        length = self._context_length(context_length)
        if not hasattr(self.model, "peft_config"):
            self.model = get_peft_model(
                self.model,
                LoraConfig(
                    r=cfg.lora.r,
                    lora_alpha=cfg.lora.alpha,
                    lora_dropout=cfg.lora.dropout,
                    target_modules=cfg.lora.target_modules or LORA_TARGET_MODULES,
                ),
            )

        def loss(x: NDArray[np.float32], y: NDArray[np.float32]) -> Any:
            valid = ~np.isnan(y).any(axis=(1, 2)) & ~np.isnan(x).all(axis=(1, 2))
            if not valid.any():
                raise ValueError(
                    "no TimesFM training pair has an observed context and complete target"
                )
            _, series = self._series(x[valid])
            targets = torch.as_tensor(
                y[valid, 0], device=self.cfg.device, dtype=torch_dtype(self.cfg)
            )
            return self.model(
                past_values=series, future_values=targets, forecast_context_len=length
            ).loss

        train_model(
            self.model,
            train,
            val,
            cfg,
            self.cfg,
            context_length,
            horizon,
            reporter,
            loss,
            channel_independent=True,
        )

    def save_adapter(self, path: Path) -> None:
        if not hasattr(self.model, "peft_config"):
            raise CapabilityError("timesfm25 has no fitted LoRA adapter")
        self.model.save_pretrained(path)

    def load_adapter(self, path: Path) -> None:
        with checkpoint_loading(self.name, path):
            from peft import PeftModel

            if hasattr(self.model, "peft_config"):
                self.model = self.model.unload()
            self.model = PeftModel.from_pretrained(self.model, path, is_trainable=True).to(
                self.cfg.device
            )
            self.model.eval()
