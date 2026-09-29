"""Unscaled NaN-aware statistics; all-NaN channels produce zeros and a warning."""

from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from tsllm.backbones.base import Backbone, Capabilities
from tsllm.backbones.registry import register_backbone
from tsllm.data.types import ContextBatch


@register_backbone()
class FeaturesBackbone(Backbone):
    name: ClassVar[str] = "features"
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes=set(), embed=True, quantiles=False, multivariate="none"
    )

    def embed(self, batch: ContextBatch) -> NDArray[np.float32]:
        self._check_batch(batch)
        batch_size, channels, _ = batch.values.shape
        result = np.zeros((batch_size, channels, 6), dtype=np.float32)
        missing = 0
        for b in range(batch_size):
            for c in range(channels):
                row = batch.values[b, c]
                positions = np.flatnonzero(~np.isnan(row)).astype(np.float64)
                if not len(positions):
                    missing += 1
                    continue
                values = row[~np.isnan(row)].astype(np.float64)
                centered = positions - positions.mean()
                slope = (
                    0.0 if len(values) == 1 else float(centered @ values / (centered @ centered))
                )
                result[b, c] = (
                    values.mean(),
                    values.std(),
                    values[-1],
                    slope,
                    values.min(),
                    values.max(),
                )
        if missing:
            self.reporter.log(f"all-NaN context channels: {missing}", level="warning")
        return result.reshape(batch_size, -1)
