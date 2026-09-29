"""Sample windows inside individual SegmentSet arrays."""

import numpy as np
from numpy.typing import NDArray

from tsllm.data.types import SegmentSet


def sample_training_windows(
    segment_set: SegmentSet,
    context_length: int,
    horizon: int,
    n: int,
    rng: np.random.Generator,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    if min(context_length, horizon, n) < 1:
        raise ValueError("window lengths and sample count must be positive")
    channels = len(segment_set.channel_names)
    if not channels or any(a.ndim != 2 or a.shape[0] != channels for a in segment_set.arrays):
        raise ValueError("segments must have shape (C, T) with matching channel names")
    arrays = [a for a in segment_set.arrays if a.shape[1] >= context_length + horizon]
    if not arrays:
        raise ValueError("no segment is long enough for the context and target window")
    lengths = np.asarray([a.shape[1] for a in arrays], dtype=np.float64)
    choices = rng.choice(len(arrays), size=n, p=lengths / lengths.sum())
    contexts = np.empty((n, channels, context_length), dtype=np.float32)
    targets = np.empty((n, channels, horizon), dtype=np.float32)
    for index, choice in enumerate(choices):
        array = arrays[choice]
        start = int(rng.integers(array.shape[1] - context_length - horizon + 1))
        boundary = start + context_length
        contexts[index] = array[:, start:boundary]
        targets[index] = array[:, boundary : boundary + horizon]
    return contexts, targets
