"""Job submission, worker subprocesses, cancel, and restart recovery."""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import psutil
from fastapi.testclient import TestClient

from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import JobSpec, RunConfig
from tsllm.runs.store import RunStore
from tsllm.service.settings import Settings

from .conftest import SLEEP_COMMAND, wait_for, wait_until


def _gone(pid: int) -> bool:
    try:
        process = psutil.Process(pid)
        return not process.is_running() or process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


def _run_body(forecast_run: Callable[..., RunConfig], **backbone: str) -> dict:
    body = forecast_run("persistence", "zero_shot").model_dump(mode="json")
    body["backbone"] |= backbone
    return body


def test_ingest_and_persistence_run_succeed(
    client: TestClient, forecast_run: Callable[..., RunConfig]
) -> None:
    response = client.post("/api/datasets/synthetic/ingest")
    assert response.status_code == 201, response.json()
    ingest_id = response.json()["run_id"]
    assert response.json()["status"]["state"] == "queued"

    response = client.post("/api/runs", json=_run_body(forecast_run))
    assert response.status_code == 201, response.json()
    run_id = response.json()["run_id"]

    assert wait_for(client, ingest_id, {"succeeded", "failed"})["status"]["state"] == "succeeded"
    detail = wait_for(client, run_id, {"succeeded", "failed"})
    assert detail["status"]["state"] == "succeeded", detail["status"]
    assert detail["job"]["run"]["backbone"]["name"] == "persistence"
    assert detail["env"]["backbone"]["name"] == "persistence"

    summaries = {s["run_id"]: s for s in client.get("/api/runs").json()}
    assert summaries[run_id]["state"] == "succeeded" and summaries[ingest_id]["kind"] == "ingest"

    metrics = client.get(f"/api/runs/{run_id}/metrics").json()
    assert metrics["task"] == "forecast" and set(metrics["splits"]) == {"val", "test"}

    origins = client.get(f"/api/runs/{run_id}/predictions", params={"split": "test"}).json()
    assert origins["total_origins"] == metrics["splits"]["test"]["n_origins"]
    assert origins["origins"] == sorted(origins["origins"]) and origins["rows"] is None
    thinned = client.get(
        f"/api/runs/{run_id}/predictions", params={"split": "test", "limit": 3}
    ).json()
    assert len(thinned["origins"]) == 3
    assert thinned["origins"][0] == origins["origins"][0]
    assert thinned["origins"][-1] == origins["origins"][-1]

    origin = origins["origins"][0]
    rows = client.get(
        f"/api/runs/{run_id}/predictions", params={"split": "test", "origin_time": origin}
    ).json()["rows"]
    assert len(rows) == 3 * 10 and {row["channel"] for row in rows} == {
        "late",
        "operating",
        "signal",
    }
    one = client.get(
        f"/api/runs/{run_id}/predictions",
        params={"split": "test", "origin_time": origin, "channel": "signal"},
    ).json()["rows"]
    assert [row["lead"] for row in one] == list(range(1, 11))
    assert {"origin_time", "channel", "lead", "y_true", "y_pred"} <= set(one[0])

    missing = client.get(f"/api/runs/{ingest_id}/metrics")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "RESULT_NOT_FOUND"


TREE_COMMAND = [
    sys.executable,
    "-c",
    "import subprocess, sys, time; "
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)', 'grandchild']); "
    "time.sleep(120)",
]


def _descendants(pid: int) -> list[psutil.Process]:
    try:
        return psutil.Process(pid).children(recursive=True)
    except psutil.NoSuchProcess:
        return []


def _has_grandchild(pid: int) -> bool:
    for process in _descendants(pid):
        try:
            if "grandchild" in process.cmdline():
                return True
        except psutil.Error:
            continue
    return False


def test_cancel_started_and_queued_jobs(
    make_client: Callable[..., TestClient], forecast_run: Callable[..., RunConfig]
) -> None:
    client = make_client(worker_command=TREE_COMMAND, cpu_slots=1)
    jobs = client.app.state.jobs  # type: ignore[attr-defined]
    first = client.post("/api/runs", json=_run_body(forecast_run)).json()["run_id"]
    second = client.post("/api/runs", json=_run_body(forecast_run)).json()["run_id"]
    wait_until(lambda: jobs.pid(first) is not None and _has_grandchild(jobs.pid(first)))
    pid = jobs.pid(first)
    tree = [pid, *(process.pid for process in _descendants(pid))]
    assert jobs.pid(second) is None

    response = client.post(f"/api/runs/{second}/cancel")
    assert response.status_code == 200 and response.json()["state"] == "cancelled"

    response = client.post(f"/api/runs/{first}/cancel")
    assert response.status_code == 200 and response.json()["state"] == "cancelled"
    assert all(_gone(member) for member in tree)
    assert client.get(f"/api/runs/{second}").json()["status"]["state"] == "cancelled"
    # The cancelled queued run is skipped; the slot stays free for new work.
    third = client.post("/api/runs", json=_run_body(forecast_run)).json()["run_id"]
    wait_until(lambda: jobs.pid(third) is not None)
    assert jobs.pid(second) is None

    again = client.post(f"/api/runs/{first}/cancel")
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_TRANSITION"


def test_cuda_jobs_use_the_gpu_pool(
    make_client: Callable[..., TestClient], forecast_run: Callable[..., RunConfig]
) -> None:
    client = make_client(worker_command=SLEEP_COMMAND, gpu_slots=1, cpu_slots=1)
    jobs = client.app.state.jobs  # type: ignore[attr-defined]
    cuda = _run_body(forecast_run, device="cuda", dtype="fp32")
    gpu_first = client.post("/api/runs", json=cuda).json()["run_id"]
    gpu_second = client.post("/api/runs", json=cuda).json()["run_id"]
    cpu = client.post("/api/runs", json=_run_body(forecast_run)).json()["run_id"]
    wait_until(lambda: jobs.pid(gpu_first) is not None and jobs.pid(cpu) is not None)
    assert jobs.pid(gpu_second) is None
    for run_id in (gpu_second, gpu_first, cpu):
        assert client.post(f"/api/runs/{run_id}/cancel").json()["state"] == "cancelled"


def test_worker_exit_without_final_state_is_failed(
    make_client: Callable[..., TestClient], forecast_run: Callable[..., RunConfig]
) -> None:
    script = (
        "import sys; from pathlib import Path; from tsllm.runs.store import RunStore; "
        "d = Path(sys.argv[1]); RunStore(d.parent).transition(d.name, 'running', writer='worker'); "
        "sys.exit(3)"
    )
    client = make_client(worker_command=[sys.executable, "-c", script])
    run_id = client.post("/api/runs", json=_run_body(forecast_run)).json()["run_id"]
    status = wait_for(client, run_id, {"failed", "succeeded"})["status"]
    assert status["state"] == "failed" and status["error"] == "worker exited with code 3"


def test_worker_exit_before_running_is_failed(
    make_client: Callable[..., TestClient], forecast_run: Callable[..., RunConfig]
) -> None:
    client = make_client(worker_command=[sys.executable, "-c", "import sys; sys.exit(2)"])
    run_id = client.post("/api/runs", json=_run_body(forecast_run)).json()["run_id"]
    status = wait_for(client, run_id, {"failed", "succeeded"})["status"]
    assert status["state"] == "failed"
    assert status["error"] == "worker exited with code 2 before it started"
    assert status["started_at"] is None and status["finished_at"] is not None


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_restart_recovery(
    make_client: Callable[..., TestClient],
    service_settings: Settings,
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
) -> None:
    store = RunStore(service_settings.runs_dir)
    ingest = JobSpec(kind="ingest", dataset=ingested_config)
    dead = store.create(ingest)
    store.transition(dead, "running", writer="worker", pid=_dead_pid())
    alive = store.create(ingest)
    alive_dir = store.path(alive).resolve()
    worker = subprocess.Popen(
        [*SLEEP_COMMAND, "tsllm.runs.worker", str(alive_dir)],
    )
    store.transition(alive, "running", writer="worker", pid=worker.pid)
    queued = store.create(
        JobSpec(
            kind="experiment", dataset=ingested_config, run=forecast_run("persistence", "zero_shot")
        )
    )

    client = make_client()
    dead_status = client.get(f"/api/runs/{dead}").json()["status"]
    assert dead_status["state"] == "interrupted" and dead_status["finished_at"] is not None
    assert client.get(f"/api/runs/{alive}").json()["status"]["state"] == "running"
    assert wait_for(client, queued, {"succeeded", "failed"})["status"]["state"] == "succeeded"

    # A reattached worker that ends without a final state is recorded as failed.
    worker.kill()
    worker.wait()
    status = wait_for(client, alive, {"failed"})["status"]
    assert status["error"].startswith("worker exited with code")
    assert not Path(alive_dir / "worker.log").exists()
