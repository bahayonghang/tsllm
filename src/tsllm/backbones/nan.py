"""Context-only missing-value handling and fit-stat scaling."""

import numpy as np
from numpy.typing import NDArray

from tsllm.backbones.base import BackboneLoadError
from tsllm.data.stats import FitStats
from tsllm.reporting import Reporter


def last_observed(values: NDArray[np.float32]) -> NDArray[np.float32]:
    indices = values.shape[-1] - 1 - np.argmax(~np.isnan(values[..., ::-1]), axis=-1)
    result = np.take_along_axis(values, indices[..., None], axis=-1)[..., 0]
    return result.astype(np.float32)


def interpolate_1d(values: NDArray[np.float32]) -> NDArray[np.float32]:
    """Strip leading NaN; interpolate gaps; hold the last observed value."""
    valid = np.flatnonzero(~np.isnan(values))
    if not len(valid):
        return np.empty(0, dtype=np.float32)
    positions = np.arange(valid[0], len(values))
    return np.interp(positions, valid, values[valid]).astype(np.float32)


def ffill_bfill(values: NDArray[np.float32]) -> NDArray[np.float32]:
    """Forward fill, backward fill leading gaps, and replace all-NaN rows with zero."""
    result = values.copy()
    for row in result.reshape(-1, result.shape[-1]):
        valid = np.flatnonzero(~np.isnan(row))
        if not len(valid):
            row.fill(0)
            continue
        indices = np.maximum.accumulate(np.where(~np.isnan(row), np.arange(len(row)), valid[0]))
        row[:] = row[indices]
    return result


def fit_scaling(
    stats: FitStats | None,
    channels: list[str],
    reporter: Reporter,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    if stats is None:
        raise BackboneLoadError("fit statistics are required")
    means, scales = [], []
    for name in channels:
        item = stats.channels.get(name)
        if item is None or item.mean is None:
            raise BackboneLoadError(f"fit statistics are missing for channel '{name}'")
        scale = item.std
        if scale is None or scale == 0:
            reporter.log(
                f"channel '{name}' has no positive fit standard deviation; using scale 1",
                level="warning",
            )
            scale = 1.0
        if not np.isfinite(item.mean) or not np.isfinite(scale) or scale < 0:
            raise BackboneLoadError(f"fit statistics are invalid for channel '{name}'")
        means.append(item.mean)
        scales.append(scale)
    return (
        np.asarray(means, dtype=np.float32)[None, :, None],
        np.asarray(scales, dtype=np.float32)[None, :, None],
    )
