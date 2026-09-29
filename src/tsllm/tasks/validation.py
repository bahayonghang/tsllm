"""Job checks before a worker loads data or a model."""

from pathlib import Path
from typing import ClassVar

from tsllm.backbones import list_backbones
from tsllm.backbones.base import BackboneLoadError, CapabilityError
from tsllm.config.run import JobSpec
from tsllm.data.cache import DatasetNotIngested, is_fresh
from tsllm.errors import TsllmError


class TaskConfigError(TsllmError):
    code: ClassVar[str] = "TASK_CONFIG_INVALID"


def validate_job(job: JobSpec, cache_root: Path | None = None) -> None:
    """Check capabilities, lengths, channel roles, and dataset cache for an experiment job."""
    run = job.run
    if run is None:
        return
    roles = {ch.role for ch in job.dataset.channels or []}
    if "known_future_covariate" in roles:
        raise NotImplementedError("known future covariate channels are not implemented")
    if run.task.type == "forecast" and "past_covariate" in roles:
        raise NotImplementedError("past covariates are not implemented for forecasting")

    infos = {info.name: info for info in list_backbones()}
    name = run.backbone.name
    if name not in infos:
        raise BackboneLoadError(f"backbone '{name}' is not registered")
    caps = infos[name].capabilities
    if run.task.type == "forecast":
        if run.mode not in caps.forecast_modes:
            raise CapabilityError(f"backbone '{name}' does not support mode '{run.mode}'")
        if caps.max_horizon is not None and run.task.horizon > caps.max_horizon:
            raise CapabilityError(f"backbone '{name}' supports horizon at most {caps.max_horizon}")
    elif not caps.embed:
        raise CapabilityError(f"backbone '{name}' does not support embeddings")
    if caps.max_context is not None and run.task.context_length > caps.max_context:
        raise CapabilityError(f"backbone '{name}' supports context at most {caps.max_context}")

    if not is_fresh(job.dataset, cache_root):
        raise DatasetNotIngested(f"dataset '{job.dataset.id}' cache is missing or stale")
