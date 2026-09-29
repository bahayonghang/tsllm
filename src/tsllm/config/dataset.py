"""Dataset source and preparation configuration."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from tsllm.config.base import Duration, StrictModel

SplitName = Literal["fit", "val", "cal", "test"]
SPLIT_NAMES: tuple[SplitName, ...] = ("fit", "val", "cal", "test")
RESERVED_COLUMNS = {"time", "observed", "eligible", "segment_id", "split", "_n"}


class SourceConfig(StrictModel):
    path: Path = Field(description="Source file path.")
    format: Literal["csv", "parquet"] = Field(default="csv", description="Source format.")
    encoding: Literal["utf8", "utf8-lossy"] = Field(default="utf8", description="CSV encoding.")
    time_column: str = Field(min_length=1, description="Timestamp column name.")
    time_format: str | None = Field(default=None, description="Timestamp format, or ISO discovery.")


class ChannelSpec(StrictModel):
    name: str = Field(min_length=1, description="Exact source column name.")
    role: Literal["target", "past_covariate", "known_future_covariate", "ignore"] = Field(
        default="target", description="Channel role."
    )
    unit: str | None = Field(default=None, description="Physical unit.")
    description: str | None = Field(default=None, description="Channel documentation.")


class Condition(StrictModel):
    channel: str = Field(min_length=1, description="Channel to compare.")
    op: Literal["gt", "ge", "lt", "le", "eq", "ne"] = Field(description="Comparison.")
    value: float = Field(allow_inf_nan=False, description="Comparison threshold.")


class ConditionGroup(StrictModel):
    all: list[Condition | ConditionGroup] | None = Field(
        default=None, min_length=1, description="All child rules must match."
    )
    any: list[Condition | ConditionGroup] | None = Field(
        default=None, min_length=1, description="At least one child rule must match."
    )

    @model_validator(mode="after")
    def one_group(self) -> Self:
        if (self.all is None) == (self.any is None):
            raise ValueError("exactly one of all or any is required")
        return self


class SegmentConfig(StrictModel):
    max_gap: Duration = Field(description="Maximum internal interruption duration.")
    min_length: Duration = Field(description="Minimum segment duration, including grid steps.")


class SplitConfig(StrictModel):
    ratios: tuple[float, float, float, float] = Field(
        default=(0.7, 0.1, 0.1, 0.1), description="Fit, val, cal, test proportions."
    )
    basis: Literal["eligible_points"] = Field(
        default="eligible_points", description="Boundary count basis."
    )

    @model_validator(mode="after")
    def valid_ratios(self) -> Self:
        if not all(math.isfinite(r) and r > 0 for r in self.ratios):
            raise ValueError("split ratios must be finite and positive")
        if not math.isclose(sum(self.ratios), 1.0, abs_tol=1e-9):
            raise ValueError("split ratios must sum to one")
        return self


class DatasetConfig(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", description="Dataset file stem.")
    source: SourceConfig = Field(description="Source file configuration.")
    native_freq: Duration = Field(description="Native sampling interval.")
    freq: Duration = Field(description="Prepared grid interval.")
    aggregation: Literal["mean", "last"] = Field(default="mean", description="Bin aggregation.")
    dedup: Literal["keep_first", "keep_last"] = Field(
        default="keep_last", description="Duplicate policy."
    )
    channels: list[ChannelSpec] | None = Field(
        default=None, min_length=1, description="Channels, or automatic numeric discovery."
    )
    eligibility: ConditionGroup | None = Field(
        default=None, description="Eligibility rules, or any non-null channel."
    )
    segments: SegmentConfig = Field(description="Continuous segment rules.")
    split: SplitConfig = Field(
        default_factory=SplitConfig, description="Chronological split rules."
    )

    @model_validator(mode="after")
    def valid_channels(self) -> Self:
        if self.channels is not None:
            names = [ch.name for ch in self.channels]
            if len(names) != len(set(names)):
                raise ValueError("channel names must be unique")
            selected = {ch.name for ch in self.channels if ch.role != "ignore"}
            if not selected or selected & (RESERVED_COLUMNS | {self.source.time_column}):
                raise ValueError("selected channels must exclude reserved and timestamp columns")
        return self
