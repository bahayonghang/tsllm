"""Dataset list, detail, plot series, channel dictionary, and ingest jobs."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import JobSpec
from tsllm.data.cache import cache_status, config_hash, is_fresh, read_cache, read_meta
from tsllm.data.channels import update_channels
from tsllm.data.registry import list_datasets, load_dataset
from tsllm.data.series import downsample_series
from tsllm.service.deps import JobsDep, SettingsDep, StoreDep
from tsllm.service.models import (
    ChannelsIn,
    ChannelsOut,
    DatasetDetailOut,
    DatasetOut,
    RunSubmittedOut,
    SeriesOut,
)
from tsllm.service.settings import Settings

router = APIRouter(tags=["datasets"])


def _dataset_out(cfg: DatasetConfig, settings: Settings) -> DatasetOut:
    return DatasetOut(
        id=cfg.id,
        status=cache_status(cfg, settings.dataset_cache_root),
        config_hash=config_hash(cfg),
        config=cfg,
    )


@router.get("/datasets")
def datasets(settings: SettingsDep) -> list[DatasetOut]:
    return [_dataset_out(cfg, settings) for cfg in list_datasets(settings.datasets_dir)]


@router.get("/datasets/{dataset_id}")
def dataset(dataset_id: str, settings: SettingsDep) -> DatasetDetailOut:
    cfg = load_dataset(dataset_id, settings.datasets_dir)
    return DatasetDetailOut(
        **_dataset_out(cfg, settings).model_dump(),
        meta=read_meta(cfg, settings.dataset_cache_root),
    )


@router.post("/datasets/{dataset_id}/ingest", status_code=201)
async def ingest(
    dataset_id: str, settings: SettingsDep, store: StoreDep, jobs: JobsDep
) -> RunSubmittedOut:
    cfg = load_dataset(dataset_id, settings.datasets_dir)
    run_id = await jobs.submit(JobSpec(kind="ingest", dataset=cfg))
    return RunSubmittedOut(run_id=run_id, status=store.read_status(run_id))


@router.get("/datasets/{dataset_id}/series")
def series(
    dataset_id: str,
    settings: SettingsDep,
    channels: Annotated[list[str] | None, Query(description="Repeat for each channel.")] = None,
    start: datetime | None = None,
    end: datetime | None = None,
    max_points: Annotated[int, Query(ge=1, le=20000)] = 2000,
) -> SeriesOut:
    """Bucket means over [start, end]; times are dataset-local and offsets are ignored."""
    cfg = load_dataset(dataset_id, settings.datasets_dir)
    prepared = read_cache(cfg, settings.dataset_cache_root)
    return SeriesOut.model_validate(downsample_series(prepared, channels, start, end, max_points))


@router.put("/datasets/{dataset_id}/channels")
def put_channels(dataset_id: str, body: ChannelsIn, settings: SettingsDep) -> ChannelsOut:
    cfg = update_channels(
        dataset_id, body.channels, settings.datasets_dir, settings.dataset_cache_root
    )
    return ChannelsOut(
        config_hash=config_hash(cfg),
        needs_ingest=not is_fresh(cfg, settings.dataset_cache_root),
        config=cfg,
    )
