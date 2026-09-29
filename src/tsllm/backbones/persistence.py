"""Repeat the last non-NaN context value, or NaN for an empty channel. No scaling."""

from typing import ClassVar

import numpy as np

from tsllm.backbones.base import Backbone, Capabilities, ForecastOutput
from tsllm.backbones.nan import last_observed
from tsllm.backbones.registry import register_backbone
from tsllm.data.types import ContextBatch


@register_backbone()
class PersistenceBackbone(Backbone):
    name: ClassVar[str] = "persistence"
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"zero_shot"},
        embed=False,
        quantiles=False,
        multivariate="channel_independent",
    )

    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput:
        self._check_batch(batch, horizon)
        return ForecastOutput(np.repeat(last_observed(batch.values)[..., None], horizon, axis=-1))
