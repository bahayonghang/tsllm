"""Run directories and the run state machine."""

import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ValidationError

from tsllm.config.io import dump_json, dump_yaml, load_json, load_yaml
from tsllm.config.run import JobSpec
from tsllm.errors import TsllmError

RunState = Literal["queued", "running", "succeeded", "failed", "cancelled", "interrupted"]
Writer = Literal["worker", "service"]

TERMINAL_STATES: frozenset[RunState] = frozenset(
    {"succeeded", "failed", "cancelled", "interrupted"}
)
ALLOWED_TRANSITIONS: frozenset[tuple[RunState, RunState, Writer]] = frozenset(
    {
        ("queued", "running", "worker"),
        ("running", "succeeded", "worker"),
        ("running", "failed", "worker"),
        ("running", "failed", "service"),
        ("queued", "failed", "service"),
        ("queued", "cancelled", "service"),
        ("running", "cancelled", "service"),
        ("running", "interrupted", "service"),
    }
)


class InvalidTransition(TsllmError):
    code: ClassVar[str] = "INVALID_TRANSITION"


class RunNotFound(TsllmError):
    code: ClassVar[str] = "RUN_NOT_FOUND"


class RunStatus(BaseModel):
    state: RunState
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pid: int | None = None
    error: str | None = None


class RunSummary(BaseModel):
    run_id: str
    name: str
    kind: Literal["experiment", "ingest"]
    dataset: str
    task: str | None
    backbone: str | None
    mode: str | None
    state: RunState
    created_at: datetime
    finished_at: datetime | None
    primary_metric: str | None
    primary_value: float | None


def _now() -> datetime:
    return datetime.now(UTC)


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:40].strip("-") or "run"


def job_name(job: JobSpec) -> str:
    return job.run.name if job.run is not None else f"ingest-{job.dataset.id}"


class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create(self, job: JobSpec) -> str:
        """Create a queued run directory; the caller acts as the service writer."""
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = _now().strftime("%Y%m%d-%H%M%S")
        while True:
            run_id = f"{stamp}-{_slug(job_name(job))}-{secrets.token_hex(2)}"
            try:
                (self.root / run_id).mkdir()
                break
            except FileExistsError:
                continue
        dump_yaml(job, self.root / run_id / "config.yaml")
        # status.json is written last. A directory without it is incomplete.
        self._write_status(run_id, RunStatus(state="queued", created_at=_now()))
        return run_id

    def path(self, run_id: str) -> Path:
        path = self.root / run_id
        if re.fullmatch(r"[A-Za-z0-9_.-]+", run_id) is None or not path.is_dir():
            raise RunNotFound(f"run '{run_id}' was not found")
        return path

    def read_status(self, run_id: str) -> RunStatus:
        path = self.path(run_id) / "status.json"
        if not path.is_file():
            raise RunNotFound(f"run '{run_id}' has no status")
        return RunStatus.model_validate(load_json(path))

    def transition(self, run_id: str, to: RunState, *, writer: Writer, **fields: Any) -> RunStatus:
        status = self.read_status(run_id)
        if (status.state, to, writer) not in ALLOWED_TRANSITIONS:
            raise InvalidTransition(
                f"run '{run_id}' cannot change from '{status.state}' to '{to}' by {writer}"
            )
        update: dict[str, Any] = {"state": to, **fields}
        if to == "running":
            update["started_at"] = _now()
        if to in TERMINAL_STATES:
            update["finished_at"] = _now()
        status = status.model_validate(status.model_dump() | update)
        self._write_status(run_id, status)
        return status

    def _write_status(self, run_id: str, status: RunStatus) -> None:
        dump_json(status.model_dump(mode="json"), self.root / run_id / "status.json")

    def read_job(self, run_id: str) -> JobSpec:
        return load_yaml(JobSpec, self.path(run_id) / "config.yaml")

    def read_metrics(self, run_id: str) -> dict[str, Any] | None:
        path = self.path(run_id) / "metrics.json"
        return load_json(path) if path.is_file() else None

    def list(self) -> list[RunSummary]:
        if not self.root.is_dir():
            return []
        summaries = []
        for directory in self.root.iterdir():
            if not (directory / "status.json").is_file():
                continue
            try:
                summaries.append(self._summary(directory.name))
            except (OSError, ValueError, ValidationError):
                # A run directory from an incompatible version is not listed.
                continue
        return sorted(summaries, key=lambda s: s.created_at, reverse=True)

    def _summary(self, run_id: str) -> RunSummary:
        status = self.read_status(run_id)
        job = self.read_job(run_id)
        metric_name = metric_value = None
        metrics = self.read_metrics(run_id)
        overall = (metrics or {}).get("splits", {}).get("test", {}).get("overall") or {}
        for name, value in overall.items():
            if isinstance(value, (int, float)):
                metric_name, metric_value = name, float(value)
                break
        run = job.run
        return RunSummary(
            run_id=run_id,
            name=job_name(job),
            kind=job.kind,
            dataset=job.dataset.id,
            task=run.task.type if run else None,
            backbone=run.backbone.name if run else None,
            mode=run.mode if run else None,
            state=status.state,
            created_at=status.created_at,
            finished_at=status.finished_at,
            primary_metric=metric_name,
            primary_value=metric_value,
        )
