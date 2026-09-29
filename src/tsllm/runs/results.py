"""Read run results: metrics and prediction tables."""

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import polars as pl

from tsllm.config.io import load_json
from tsllm.errors import TsllmError
from tsllm.runs.store import RunStore


class ResultNotFound(TsllmError):
    code: ClassVar[str] = "RESULT_NOT_FOUND"


def read_metrics(store: RunStore, run_id: str) -> dict[str, Any]:
    metrics = store.read_metrics(run_id)
    if metrics is None:
        raise ResultNotFound(f"run '{run_id}' has no metrics")
    return metrics


def _predictions(store: RunStore, run_id: str, split: str) -> pl.LazyFrame:
    path: Path = store.path(run_id) / "predictions" / f"{split}.parquet"
    if not path.is_file():
        raise ResultNotFound(f"run '{run_id}' has no predictions for split '{split}'")
    return pl.scan_parquet(path)


def prediction_origins(
    store: RunStore, run_id: str, split: str, limit: int
) -> tuple[list[datetime], int]:
    """Sorted unique origins, evenly thinned to at most limit items, and the total count."""
    origins = (
        _predictions(store, run_id, split)
        .select(pl.col("origin_time").unique().sort())
        .collect()["origin_time"]
    )
    total = origins.len()
    if total > limit:
        origins = origins.gather(np.unique(np.linspace(0, total - 1, limit).round().astype(int)))
    return origins.to_list(), total


def prediction_rows(
    store: RunStore, run_id: str, split: str, origin_time: datetime, channel: str | None
) -> list[dict[str, Any]]:
    """All rows of one origin. Forecast rows are filtered by channel when channel is set."""
    frame = _predictions(store, run_id, split)
    columns = frame.collect_schema().names()
    # Prediction times have no time zone. A request offset is ignored, not converted.
    frame = frame.filter(pl.col("origin_time") == origin_time.replace(tzinfo=None))
    if channel is not None and "channel" in columns:
        frame = frame.filter(pl.col("channel") == channel)
    order = [name for name in ("channel", "lead") if name in columns]
    if order:
        frame = frame.sort(order)
    return frame.with_columns(pl.col(pl.Float32, pl.Float64).fill_nan(None)).collect().to_dicts()


def read_env(store: RunStore, run_id: str) -> dict[str, Any] | None:
    path = store.path(run_id) / "env.json"
    return load_json(path) if path.is_file() else None
