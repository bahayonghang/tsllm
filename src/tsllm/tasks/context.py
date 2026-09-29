"""Inputs shared by task functions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tsllm.backbones import Backbone, get_backbone
from tsllm.config.io import dump_json
from tsllm.config.run import JobSpec, RunConfig
from tsllm.data.stats import FitStats
from tsllm.data.types import PreparedFrame
from tsllm.evaluation.resources import Timer
from tsllm.reporting import Reporter


@dataclass
class TaskContext:
    run_dir: Path
    job: JobSpec
    run: RunConfig
    prepared: PreparedFrame
    fit_stats: FitStats
    reporter: Reporter
    backbone: Backbone | None = None

    def write_json(self, name: str, payload: Any) -> None:
        dump_json(payload, self.run_dir / name)

    def load_backbone(self) -> tuple[Backbone, float]:
        """Load the configured backbone and return it with the load time in seconds."""
        backbone = get_backbone(self.run.backbone.name)
        with Timer() as timer:
            backbone.load(self.run.backbone, self.fit_stats, reporter=self.reporter)
        self.backbone = backbone
        return backbone, timer.seconds
