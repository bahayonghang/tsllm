import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from tsllm.backbones import list_backbones
from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import ForecastTaskConfig, JobSpec, RunConfig
from tsllm.config.schema import run_config_schema


def test_schema_serializes_with_task_union_and_backbone_options() -> None:
    schema = run_config_schema()
    json.dumps(schema, ensure_ascii=False)
    run_schema = schema["run_config"]
    task = run_schema["properties"]["task"]
    assert set(task["discriminator"]["mapping"]) == {"forecast", "classify"}
    assert set(schema["backbone_options"]) == {info.name for info in list_backbones()}
    for name in ("ForecastTaskConfig", "ClassifyTaskConfig", "HeadConfig", "FutureEventRule"):
        properties = run_schema["$defs"][name]["properties"]
        assert all("description" in field for field in properties.values()), name


def test_run_config_rules(
    forecast_run: Callable[..., RunConfig], classify_run: Callable[..., RunConfig]
) -> None:
    run = forecast_run("persistence", "zero_shot")
    assert isinstance(run.task, ForecastTaskConfig)
    assert RunConfig.model_validate(run.model_dump(mode="json")) == run
    with pytest.raises(ValidationError, match="leads"):
        forecast_run("persistence", "zero_shot", eval_leads=[11])
    with pytest.raises(ValidationError):
        forecast_run("persistence", "zero_shot", eval_splits=["fit"])
    payload = classify_run().model_dump(mode="json")
    with pytest.raises(ValidationError, match="head"):
        RunConfig.model_validate(payload | {"mode": "zero_shot"})
    with pytest.raises(ValidationError):
        RunConfig.model_validate(payload | {"unknown": 1})


def test_job_spec_rules(
    synthetic_config: DatasetConfig, forecast_run: Callable[..., RunConfig]
) -> None:
    run = forecast_run("persistence", "zero_shot")
    JobSpec(kind="experiment", dataset=synthetic_config, run=run)
    JobSpec(kind="ingest", dataset=synthetic_config)
    with pytest.raises(ValidationError):
        JobSpec(kind="experiment", dataset=synthetic_config)
    with pytest.raises(ValidationError):
        JobSpec(kind="ingest", dataset=synthetic_config, run=run)
    with pytest.raises(ValidationError, match="dataset"):
        JobSpec(
            kind="experiment",
            dataset=synthetic_config,
            run=run.model_copy(update={"dataset": "other"}),
        )
