"""Environment snapshot written to env.json."""

import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from typing import Any
from urllib.parse import urlparse

from tsllm.config.run import JobSpec

PACKAGES = (
    "tsllm",
    "transformers",
    "peft",
    "chronos-forecasting",
    "granite-tsfm",
    "polars",
    "numpy",
    "scikit-learn",
)


def _version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _torch() -> dict[str, Any] | None:
    if find_spec("torch") is None:
        return None
    import torch

    info: dict[str, Any] = {
        "version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": None,
        "compute_capability": None,
    }
    if info["cuda_available"]:
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["compute_capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
    return info


def environment_snapshot(
    job: JobSpec,
    *,
    license: str | None = None,
    resolved_checkpoint: str | None = None,
    resolved_revision: str | None = None,
) -> dict[str, Any]:
    endpoint = os.environ.get("HF_ENDPOINT")
    backbone = job.run.backbone if job.run is not None else None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {package: _version(package) for package in PACKAGES},
        "torch": _torch(),
        "backbone": None
        if backbone is None
        else {
            "name": backbone.name,
            "checkpoint": backbone.checkpoint,
            "revision": backbone.revision,
            "resolved_checkpoint": resolved_checkpoint,
            "resolved_revision": resolved_revision,
            "license": license,
        },
        "hf_endpoint": {
            "set": endpoint is not None,
            "host": urlparse(endpoint).hostname if endpoint else None,
        },
    }
