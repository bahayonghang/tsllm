import itertools
import json
import re
from pathlib import Path
from typing import get_args

import pytest

from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import JobSpec
from tsllm.runs.reporter import FileReporter
from tsllm.runs.store import (
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    RunNotFound,
    RunState,
    RunStore,
    Writer,
)


def _ingest_job(cfg: DatasetConfig) -> JobSpec:
    return JobSpec(kind="ingest", dataset=cfg)


def test_create_writes_snapshot_and_queued_status(
    synthetic_config: DatasetConfig, tmp_path: Path
) -> None:
    store = RunStore(tmp_path / "runs")
    run_id = store.create(_ingest_job(synthetic_config))
    assert re.fullmatch(r"\d{8}-\d{6}-ingest-synthetic-[0-9a-f]{4}", run_id)
    assert store.read_job(run_id) == _ingest_job(synthetic_config)
    status = store.read_status(run_id)
    assert status.state == "queued" and status.started_at is None
    assert not list(store.path(run_id).glob("*.tmp"))
    with pytest.raises(RunNotFound):
        store.read_status("missing")
    with pytest.raises(RunNotFound):
        store.path("../outside")


def test_transition_matrix(synthetic_config: DatasetConfig, tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    states: tuple[RunState, ...] = get_args(RunState)
    writers: tuple[Writer, ...] = get_args(Writer)
    paths = {
        "queued": [],
        "running": [("running", "worker")],
        "succeeded": [("running", "worker"), ("succeeded", "worker")],
        "failed": [("running", "worker"), ("failed", "worker")],
        "cancelled": [("cancelled", "service")],
        "interrupted": [("running", "worker"), ("interrupted", "service")],
    }
    for source, target, writer in itertools.product(states, states, writers):
        run_id = store.create(_ingest_job(synthetic_config))
        for state, by in paths[source]:
            store.transition(run_id, state, writer=by)
        if (source, target, writer) in ALLOWED_TRANSITIONS:
            status = store.transition(run_id, target, writer=writer)
            assert status.state == target
        else:
            with pytest.raises(InvalidTransition):
                store.transition(run_id, target, writer=writer)
            assert store.read_status(run_id).state == source


def test_transition_fields_and_list_order(synthetic_config: DatasetConfig, tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    first = store.create(_ingest_job(synthetic_config))
    second = store.create(_ingest_job(synthetic_config))
    running = store.transition(first, "running", writer="worker", pid=123)
    assert running.pid == 123 and running.started_at is not None
    failed = store.transition(first, "failed", writer="worker", error="ValueError: x")
    assert failed.error == "ValueError: x" and failed.finished_at is not None
    (tmp_path / "runs" / "incomplete").mkdir()
    assert [s.run_id for s in store.list()] == [second, first]
    assert store.list()[1].state == "failed"


def test_file_reporter_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "events.jsonl"
    clock = iter([0.0, 0.1, 0.2, 0.7])
    monkeypatch.setattr("tsllm.runs.reporter.monotonic", lambda: next(clock))
    reporter = FileReporter(path)
    reporter.stage("evaluate:test")
    for step in range(1, 5):
        reporter.progress(step, 4)
    reporter.metric("train_loss", float("nan"), step=1)
    reporter.log("通道 message", level="warning")
    lines = path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    assert [e["kind"] for e in events] == ["stage", "progress", "progress", "metric", "log"]
    # Step 2 and 3 are inside the 0.5 s interval; the last step is always written.
    assert [e["step"] for e in events if e["kind"] == "progress"] == [1, 4]
    assert events[1]["stage"] == "evaluate:test"
    assert events[3]["value"] is None and events[4]["msg"] == "通道 message"
    assert all(e["ts"].endswith("+00:00") for e in events)
