"""Request and response models of the HTTP API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from tsllm.config.dataset import ChannelSpec, DatasetConfig
from tsllm.config.run import JobSpec
from tsllm.runs.store import RunState, RunStatus

CacheState = Literal["fresh", "stale", "missing"]


class HealthOut(BaseModel):
    status: Literal["ok"] = "ok"


class GpuOut(BaseModel):
    index: int
    name: str
    memory_total_mb: float
    memory_used_mb: float
    driver_version: str


class SystemOut(BaseModel):
    python: str
    platform: str
    packages: dict[str, str | None]
    gpus: list[GpuOut]
    runs_dir: str
    cache_dir: str
    configs_dir: str
    gpu_slots: int
    cpu_slots: int


class DatasetOut(BaseModel):
    id: str
    status: CacheState = Field(description="Cache state of the current configuration.")
    config_hash: str
    config: DatasetConfig


class DatasetDetailOut(DatasetOut):
    meta: dict[str, Any] | None = Field(description="Cache metadata; null unless fresh.")


class ChannelsIn(BaseModel):
    channels: list[ChannelSpec] = Field(
        min_length=1, description="All channels; only role, unit, and description can change."
    )


class ChannelsOut(BaseModel):
    config_hash: str
    needs_ingest: bool
    config: DatasetConfig


class SegmentOut(BaseModel):
    segment_id: int
    start: datetime
    end: datetime
    length: int
    duration_seconds: float
    eligible_points: int


class SeriesOut(BaseModel):
    every: str = Field(description="Bucket width; buckets are labelled with their start time.")
    time: list[datetime]
    values: dict[str, list[float | None]]
    segments: list[SegmentOut]
    split_boundaries: dict[str, datetime]


class RunSubmittedOut(BaseModel):
    run_id: str
    status: RunStatus


class RunDetailOut(BaseModel):
    run_id: str
    job: JobSpec
    status: RunStatus
    env: dict[str, Any] | None


class PredictionsOut(BaseModel):
    split: str
    origin_time: datetime | None = Field(description="Requested origin; null for the origin list.")
    origins: list[datetime] | None = Field(description="Thinned origin list without origin_time.")
    total_origins: int | None = Field(description="Origin count before thinning.")
    rows: list[dict[str, Any]] | None = Field(description="Prediction rows of origin_time.")


class CompareColumnOut(BaseModel):
    run_id: str
    name: str
    dataset: str
    task: str | None
    backbone: str | None
    mode: str | None
    state: RunState
    context_length: int | None
    horizon: int | None


class CompareRowOut(BaseModel):
    split: str
    metric: str
    values: dict[str, float | None] = Field(description="Value per run id.")


class CompareWarningOut(BaseModel):
    code: str
    message: str


class CompareOut(BaseModel):
    columns: list[CompareColumnOut]
    rows: list[CompareRowOut]
    warnings: list[CompareWarningOut]


class TemplateOut(BaseModel):
    name: str
