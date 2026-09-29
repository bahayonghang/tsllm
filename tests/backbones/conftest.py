"""Synthetic adapter inputs and observable training reports."""

import numpy as np
import pytest

from tsllm.data.stats import ChannelStats, FitStats
from tsllm.data.types import ContextBatch, SegmentSet
from tsllm.reporting import LogLevel, NullReporter


class RecordingReporter(NullReporter):
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []
        self.metrics: list[tuple[str, float, int | None]] = []
        self.steps: list[tuple[int, int]] = []

    def log(self, msg: str, level: LogLevel = "info") -> None:
        self.logs.append((msg, level))

    def metric(self, name: str, value: float, step: int | None = None) -> None:
        self.metrics.append((name, value, step))

    def progress(self, step: int, total: int) -> None:
        self.steps.append((step, total))


@pytest.fixture
def reporter() -> RecordingReporter:
    return RecordingReporter()


def context(values: np.ndarray) -> ContextBatch:
    return ContextBatch(
        values.astype(np.float32),
        [f"channel_{c}" for c in range(values.shape[1])],
        np.full(values.shape[0], np.datetime64("2024-01-01", "us")),
        "1min",
    )


@pytest.fixture
def sine_segments() -> SegmentSet:
    time = np.arange(320, dtype=np.float32)
    values = np.stack([np.sin(time * 2 * np.pi / 16), np.cos(time * 2 * np.pi / 16)])
    return SegmentSet([values.astype(np.float32)], ["channel_0", "channel_1"], "1min")


@pytest.fixture
def unit_stats() -> FitStats:
    return FitStats({f"channel_{c}": ChannelStats(320, 0.0, 1.0, {}) for c in range(2)})
