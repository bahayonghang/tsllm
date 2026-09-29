"""Server-sent events from events.jsonl."""

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import JobSpec
from tsllm.runs.store import RunStore
from tsllm.service.settings import Settings


def _parse(text: str) -> list[dict[str, str]]:
    events = []
    for block in text.split("\n\n"):
        if not block:
            continue
        fields: dict[str, str] = {}
        for line in block.split("\n"):
            key, _, value = line.partition(": ")
            fields[key] = value
        events.append(fields)
    return events


def _append(path: Path, lines: list[dict], *, newline: bool = True) -> None:
    with path.open("a", encoding="utf-8") as stream:
        text = "\n".join(json.dumps(line, ensure_ascii=False) for line in lines)
        stream.write(text + ("\n" if newline else ""))


def _run(settings: Settings, cfg: DatasetConfig) -> tuple[RunStore, str, Path]:
    store = RunStore(settings.runs_dir)
    run_id = store.create(JobSpec(kind="ingest", dataset=cfg))
    return store, run_id, store.path(run_id) / "events.jsonl"


EVENTS = [
    {"ts": "t", "kind": "stage", "name": "read"},
    {"ts": "t", "kind": "progress", "stage": "read", "step": 1, "total": 2},
    {"ts": "t", "kind": "log", "level": "warning", "msg": "通道 a b"},
    {"ts": "t", "kind": "metric", "name": "x", "value": None, "step": None},
    {"ts": "t", "kind": "stage", "name": "done"},
]


def test_terminal_run_streams_all_events_then_end(
    client: TestClient, service_settings: Settings, ingested_config: DatasetConfig
) -> None:
    store, run_id, path = _run(service_settings, ingested_config)
    store.transition(run_id, "running", writer="worker")
    _append(path, EVENTS)
    _append(path, [{"ts": "t", "kind": "log", "level": "info", "msg": "partial"}], newline=False)
    store.transition(run_id, "succeeded", writer="worker")

    events = _parse(client.get(f"/api/runs/{run_id}/events").text)
    assert [e["id"] for e in events[:-1]] == ["1", "2", "3", "4", "5"]
    assert [e["event"] for e in events[:-1]] == [e["kind"] for e in EVENTS]
    assert [json.loads(e["data"]) for e in events[:-1]] == EVENTS
    assert events[-1] == {"event": "end", "data": '{"state": "succeeded"}'}

    resumed = _parse(client.get(f"/api/runs/{run_id}/events", headers={"Last-Event-ID": "3"}).text)
    assert [e.get("id") for e in resumed] == ["4", "5", None]
    from_query = _parse(client.get(f"/api/runs/{run_id}/events", params={"from": 4}).text)
    assert [e.get("id") for e in from_query] == ["5", None]


def test_live_run_streams_new_lines_and_heartbeats(
    make_client: Callable[..., TestClient],
    service_settings: Settings,
    ingested_config: DatasetConfig,
) -> None:
    client = make_client(heartbeat_seconds=0.1)
    store, run_id, path = _run(service_settings, ingested_config)
    store.transition(run_id, "running", writer="worker")
    _append(path, EVENTS[:2])

    def worker() -> None:
        time.sleep(0.5)
        _append(path, EVENTS[2:])
        store.transition(run_id, "failed", writer="worker", error="E: x")

    thread = threading.Thread(target=worker)
    thread.start()
    with client.stream("GET", f"/api/runs/{run_id}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        text = "".join(response.iter_text())
    thread.join()
    assert ": ping" in text
    events = [e for e in _parse(text) if "event" in e]
    assert [e.get("id") for e in events] == ["1", "2", "3", "4", "5", None]
    assert json.loads(events[-1]["data"]) == {"state": "failed"}


def test_events_of_unknown_run(client: TestClient) -> None:
    response = client.get("/api/runs/missing/events")
    assert response.status_code == 404 and response.json()["error"]["code"] == "RUN_NOT_FOUND"
