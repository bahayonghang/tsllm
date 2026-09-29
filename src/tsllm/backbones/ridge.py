"""Fit-stat normalized ridge regression. Context NaN becomes zero; NaN targets are dropped."""

from pathlib import Path
from typing import ClassVar

import numpy as np
from pydantic import BaseModel, Field

from tsllm.backbones.base import (
    Backbone,
    BackboneLoadError,
    Capabilities,
    CapabilityError,
    FinetuneMode,
    ForecastOutput,
)
from tsllm.backbones.nan import fit_scaling
from tsllm.backbones.registry import register_backbone
from tsllm.backbones.windows import sample_training_windows
from tsllm.config.backbone import FinetuneConfig
from tsllm.config.base import StrictModel
from tsllm.data.types import ContextBatch, SegmentSet
from tsllm.reporting import Reporter


class RidgeOptions(StrictModel):
    alpha: float = Field(default=1.0, ge=0, description="Ridge regularization strength.")
    max_samples: int = Field(default=50000, gt=0, description="Number of sampled training windows.")
    seed: int = Field(default=0, ge=0, description="Training-window sampling seed.")


@register_backbone(requires=["sklearn"])
class RidgeBackbone(Backbone):
    name: ClassVar[str] = "ridge"
    Options: ClassVar[type[BaseModel]] = RidgeOptions
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"full"},
        embed=False,
        quantiles=False,
        multivariate="native",
        needs_fit_stats=True,
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
        try:
            from sklearn.linear_model import Ridge
        except ImportError as exc:
            raise BackboneLoadError("ridge requires an importable scikit-learn") from exc

        x, y = sample_training_windows(
            train,
            context_length,
            horizon,
            self.options.max_samples,
            np.random.default_rng(self.options.seed),
        )
        self.means, self.scales = fit_scaling(self.fit_stats, train.channel_names, reporter)
        valid = ~np.isnan(y).any(axis=(1, 2))
        if not valid.any():
            raise ValueError("no ridge training window has a complete target")
        reporter.metric("dropped_target_windows", float((~valid).sum()))
        normalized_x = np.nan_to_num((x[valid] - self.means) / self.scales, nan=0.0)
        normalized_y = (y[valid] - self.means) / self.scales
        model = Ridge(alpha=self.options.alpha)
        model.fit(normalized_x.reshape(valid.sum(), -1), normalized_y.reshape(valid.sum(), -1))
        self.coef, self.intercept = model.coef_, model.intercept_
        self.context_length, self.horizon = context_length, horizon
        self.channels = list(train.channel_names)
        reporter.progress(1, 1)

    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput:
        self._check_batch(batch, horizon)
        if not hasattr(self, "coef"):
            raise CapabilityError("ridge must be fitted before forecasting")
        if batch.channel_names != self.channels or batch.values.shape[-1] != self.context_length:
            raise ValueError("ridge context shape or channel order differs from training")
        if horizon > self.horizon:
            raise CapabilityError(f"ridge was fitted for horizon {self.horizon}")
        values = np.nan_to_num((batch.values - self.means) / self.scales, nan=0.0)
        flat = values.reshape(len(values), -1) @ self.coef.T + self.intercept
        prediction = flat.reshape(len(values), len(self.channels), self.horizon)
        return ForecastOutput(
            (prediction * self.scales + self.means)[..., :horizon].astype(np.float32)
        )

    def save_adapter(self, path: Path) -> None:
        if not hasattr(self, "coef"):
            raise CapabilityError("ridge must be fitted before saving")
        path.mkdir(parents=True, exist_ok=True)
        np.savez(
            path / "ridge.npz",
            coef=self.coef,
            intercept=self.intercept,
            means=self.means,
            scales=self.scales,
            channels=np.asarray(self.channels),
            context_length=self.context_length,
            horizon=self.horizon,
        )

    def load_adapter(self, path: Path) -> None:
        with np.load(path / "ridge.npz", allow_pickle=False) as saved:
            self.coef, self.intercept = saved["coef"], saved["intercept"]
            self.means, self.scales = saved["means"], saved["scales"]
            self.channels = saved["channels"].tolist()
            self.context_length, self.horizon = int(saved["context_length"]), int(saved["horizon"])
