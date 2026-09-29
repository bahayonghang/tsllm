"""Health and system facts."""

import platform
import sys

from fastapi import APIRouter

from tsllm.runs.env import gpu_info, package_versions
from tsllm.service.deps import SettingsDep
from tsllm.service.models import GpuOut, HealthOut, SystemOut

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> HealthOut:
    return HealthOut()


@router.get("/system")
def system(settings: SettingsDep) -> SystemOut:
    return SystemOut(
        python=sys.version.split()[0],
        platform=platform.platform(),
        packages=package_versions(),
        gpus=[GpuOut.model_validate(gpu) for gpu in gpu_info()],
        runs_dir=str(settings.runs_dir.resolve()),
        cache_dir=str(settings.cache_dir.resolve()),
        configs_dir=str(settings.configs_dir.resolve()),
        gpu_slots=settings.gpu_slots,
        cpu_slots=settings.cpu_slots,
    )
