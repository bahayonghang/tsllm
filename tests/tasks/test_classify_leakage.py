from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import load_json
from tsllm.config.run import JobSpec, RunConfig
from tsllm.data.cache import read_cache
from tsllm.data.prepare import ingest_dataset
from tsllm.data.stats import fit_rows
from tsllm.reporting import NullReporter
from tsllm.runs.store import RunStore
from tsllm.runs.worker import main


def _threshold(cfg: DatasetConfig, run: RunConfig) -> float:
    store = RunStore(Path("runs"))
    run_id = store.create(JobSpec(kind="experiment", dataset=cfg, run=run))
    assert main(store.path(run_id)) == 0
    return load_json(store.path(run_id) / "label_info.json")["threshold"]


def test_label_threshold_uses_fit_rows_only(
    ingested_config: DatasetConfig, classify_run: Callable[..., RunConfig], tmp_path: Path
) -> None:
    run = classify_run()
    baseline = _threshold(ingested_config, run)
    fit = fit_rows(read_cache(ingested_config))
    expected = fit["signal"].cast(pl.Float64).quantile(0.9, interpolation="linear")
    assert baseline == pytest.approx(expected)

    # The last day is in val, cal, and test. Eligibility does not use this channel,
    # so the split boundaries do not change.
    source = pl.read_csv(ingested_config.source.path, try_parse_dates=True)
    late = pl.col("date") >= datetime(2024, 1, 3, 12)
    extreme = source.with_columns(
        pl.when(late).then(pl.col("signal") * 1000).otherwise(pl.col("signal")).alias("signal")
    )
    path = tmp_path / "extreme.csv"
    extreme.write_csv(path)
    changed = ingested_config.model_copy(
        update={"source": ingested_config.source.model_copy(update={"path": path})}
    )
    prepared = ingest_dataset(changed, NullReporter())
    assert prepared.meta["split_boundaries"] == read_cache(ingested_config).meta["split_boundaries"]
    fit_end = datetime.fromisoformat(prepared.meta["split_boundaries"]["val"])
    assert fit_end < datetime(2024, 1, 3, 12)
    assert _threshold(changed, run) == pytest.approx(baseline)
