"""Environment snapshot written to env.json."""

import os
import platform
import shutil
import subprocess
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


def package_versions() -> dict[str, str | None]:
    """Installed versions from package metadata. No package is imported."""
    return {package: _version(package) for package in (*PACKAGES, "torch", "fastapi")}


def gpu_info() -> list[dict[str, Any]]:
    """GPU facts from nvidia-smi, without torch. An empty list means no GPU was found."""
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return []
    query = "index,name,memory.total,memory.used,driver_version"
    try:
        result = subprocess.run(
            [executable, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    gpus = []
    for line in result.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 5:
            continue
        index, name, total, used, driver = fields
        gpus.append(
            {
                "index": int(index),
                "name": name,
                "memory_total_mb": float(total),
                "memory_used_mb": float(used),
                "driver_version": driver,
            }
        )
    return gpus
