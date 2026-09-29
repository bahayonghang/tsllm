"""Service settings from environment variables."""

import os
import sys
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field


class Settings(BaseModel):
    runs_dir: Path = Field(default=Path("runs"), description="Run directory root.")
    cache_dir: Path = Field(default=Path("cache"), description="Cache root; datasets/ below it.")
    configs_dir: Path = Field(default=Path("configs"), description="Holds datasets/ and runs/.")
    gpu_slots: int = Field(default=1, ge=1, description="Concurrent jobs with device cuda.")
    cpu_slots: int = Field(default=2, ge=1, description="Concurrent other jobs.")
    worker_command: list[str] = Field(
        default_factory=lambda: [sys.executable, "-m", "tsllm.runs.worker"],
        min_length=1,
        description="Worker command; the run directory is appended as the last argument.",
    )
    web_dist: Path = Field(default=Path("web/dist"), description="Built web UI.")
    poll_seconds: float = Field(default=0.5, gt=0, description="Process and event poll interval.")
    heartbeat_seconds: float = Field(default=15.0, gt=0, description="SSE heartbeat interval.")

    @classmethod
    def from_env(cls) -> Self:
        names = {
            "runs_dir": "TSLLM_RUNS_DIR",
            "cache_dir": "TSLLM_CACHE_DIR",
            "configs_dir": "TSLLM_CONFIGS_DIR",
            "gpu_slots": "TSLLM_GPU_SLOTS",
            "cpu_slots": "TSLLM_CPU_SLOTS",
        }
        return cls.model_validate(
            {field: os.environ[env] for field, env in names.items() if env in os.environ}
        )

    @property
    def dataset_cache_root(self) -> Path:
        return self.cache_dir / "datasets"

    @property
    def datasets_dir(self) -> Path:
        return self.configs_dir / "datasets"

    @property
    def templates_dir(self) -> Path:
        return self.configs_dir / "runs"
