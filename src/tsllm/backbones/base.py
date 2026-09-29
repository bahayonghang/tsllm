"""Backbone contract with explicit capability errors and injected reporting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.config.base import StrictModel
from tsllm.data.stats import FitStats
from tsllm.data.types import ContextBatch, SegmentSet
from tsllm.errors import TsllmError
from tsllm.reporting import Reporter

if TYPE_CHECKING:
    from tsllm.backbones.checkpoint import ResolvedCheckpoint

FinetuneMode = Literal["lora", "head", "full"]


class CapabilityError(TsllmError):
    code: ClassVar[str] = "CAPABILITY_UNSUPPORTED"


class BackboneLoadError(TsllmError):
    code: ClassVar[str] = "BACKBONE_LOAD_FAILED"


class Capabilities(StrictModel):
    forecast_modes: set[Literal["zero_shot", "lora", "head", "full"]]
    embed: bool
    quantiles: bool
    multivariate: Literal["native", "channel_independent", "none"]
    max_context: int | None = None
    max_horizon: int | None = None
    needs_fit_stats: bool = False


@dataclass(frozen=True)
class ForecastOutput:
    mean: NDArray[np.float32]  # (B, C, H), physical units.
    quantiles: NDArray[np.float32] | None = None  # (B, C, H, Q).
    quantile_levels: list[float] | None = None


class EmptyOptions(StrictModel):
    pass


class Backbone:
    name: ClassVar[str]
    capabilities: ClassVar[Capabilities]
    Options: ClassVar[type[BaseModel]] = EmptyOptions
    cfg: BackboneConfig
    fit_stats: FitStats | None
    reporter: Reporter
    options: Any
    resolved_checkpoint: ResolvedCheckpoint | None = None

    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None, *, reporter: Reporter) -> None:
        options = self.Options.model_validate(cfg.options)
        if cfg.name != self.name:
            raise BackboneLoadError(f"configuration name does not match backbone '{self.name}'")
        if self.capabilities.needs_fit_stats and fit_stats is None:
            raise BackboneLoadError(f"backbone '{self.name}' requires FitStats")
        self.cfg, self.fit_stats, self.reporter, self.options = cfg, fit_stats, reporter, options
        self.resolved_checkpoint = None

    def _check_mode(self, mode: FinetuneMode) -> None:
        if mode not in ("lora", "head", "full") or mode not in self.capabilities.forecast_modes:
            raise CapabilityError(f"backbone '{self.name}' does not support mode '{mode}'")

    def _check_batch(self, batch: ContextBatch, horizon: int | None = None) -> None:
        if batch.values.ndim != 3 or min(batch.values.shape) < 1:
            raise ValueError("context requires a nonempty (B, C, L) array")
        if len(batch.channel_names) != batch.values.shape[1]:
            raise ValueError("channel names do not match context channels")
        if np.isinf(batch.values).any():
            raise ValueError("context values must not contain infinity")
        maximum = self.capabilities.max_context
        if maximum is not None and batch.values.shape[2] > maximum:
            raise CapabilityError(f"backbone '{self.name}' supports context at most {maximum}")
        if horizon is not None:
            if not self.capabilities.forecast_modes:
                raise CapabilityError(f"backbone '{self.name}' does not support forecasting")
            if horizon < 1:
                raise ValueError("horizon must be positive")
            maximum = self.capabilities.max_horizon
            if maximum is not None and horizon > maximum:
                raise CapabilityError(f"backbone '{self.name}' supports horizon at most {maximum}")

    def _resolve(self, default_checkpoint: str) -> ResolvedCheckpoint:
        from tsllm.backbones.checkpoint import resolve_checkpoint

        cfg = self.cfg.model_copy(update={"checkpoint": self.cfg.checkpoint or default_checkpoint})
        result = resolve_checkpoint(cfg)
        self.resolved_checkpoint = result
        if cfg.revision is None:
            self.reporter.log(
                f"checkpoint revision was not pinned; resolved revision: {result.revision}",
                level="warning",
            )
        return result

    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput:
        raise CapabilityError(f"backbone '{self.name}' does not support forecasting")

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
        raise CapabilityError(f"backbone '{self.name}' does not implement fine-tuning")

    def embed(self, batch: ContextBatch) -> NDArray[np.float32]:
        raise CapabilityError(f"backbone '{self.name}' does not support embeddings")

    def save_adapter(self, path: Path) -> None:
        raise CapabilityError(f"backbone '{self.name}' has no trainable adapter")

    def load_adapter(self, path: Path) -> None:
        raise CapabilityError(f"backbone '{self.name}' has no trainable adapter")
