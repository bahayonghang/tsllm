"""Timing, latency, and GPU memory measurement."""

import sys
from time import perf_counter
from types import TracebackType

import numpy as np


class Timer:
    def __enter__(self) -> "Timer":
        self.start = perf_counter()
        self.seconds = 0.0
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.seconds = perf_counter() - self.start


def peak_vram_mb() -> float | None:
    """Peak allocated CUDA memory in this process; None when torch or CUDA is not in use."""
    # Read only an already imported torch. This module must not import model libraries.
    torch = sys.modules.get("torch")
    if torch is None or not torch.cuda.is_available() or not torch.cuda.is_initialized():
        return None
    return torch.cuda.max_memory_allocated() / 2**20


def latency_percentiles(milliseconds: list[float]) -> tuple[float | None, float | None]:
    if not milliseconds:
        return None, None
    p50, p95 = np.percentile(np.asarray(milliseconds, dtype=np.float64), [50, 95])
    return float(p50), float(p95)
