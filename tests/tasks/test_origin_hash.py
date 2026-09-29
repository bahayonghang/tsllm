from collections.abc import Callable
from pathlib import Path

from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import JobSpec, RunConfig
from tsllm.runs.store import RunStore
from tsllm.runs.worker import main


def test_same_task_config_gives_same_origin_sets(
    ingested_config: DatasetConfig, forecast_run: Callable[..., RunConfig]
) -> None:
    store = RunStore(Path("runs"))
    hashes = []
    for backbone, mode in [("persistence", "zero_shot"), ("ridge", "full")]:
        run = forecast_run(backbone, mode, max_eval_origins=20)
        run_id = store.create(JobSpec(kind="experiment", dataset=ingested_config, run=run))
        assert main(store.path(run_id)) == 0
        metrics = store.read_metrics(run_id)
        assert metrics is not None
        hashes.append({split: r["origin_set_hash"] for split, r in metrics["splits"].items()})
    assert hashes[0] == hashes[1]
    assert hashes[0]["val"] != hashes[0]["test"]
