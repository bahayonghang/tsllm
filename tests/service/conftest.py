"""Service fixtures: temporary configs, runs, and cache with an ingested synthetic dataset."""

import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tsllm.config.dataset import DatasetConfig
from tsllm.data.registry import save_dataset
from tsllm.service.app import create_app
from tsllm.service.settings import Settings

SLEEP_COMMAND = [sys.executable, "-c", "import time; time.sleep(120)"]


@pytest.fixture
def service_settings(
    ingested_config: DatasetConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Settings:
    monkeypatch.delenv("TSLLM_CACHE_DIR", raising=False)
    (tmp_path / "configs" / "datasets").mkdir(parents=True)
    save_dataset(ingested_config, tmp_path / "configs" / "datasets")
    return Settings(
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        configs_dir=tmp_path / "configs",
        web_dist=tmp_path / "web" / "dist",
        poll_seconds=0.05,
    )


@pytest.fixture
def make_client(service_settings: Settings) -> Iterator[Callable[..., TestClient]]:
    """Start an app with optional Settings overrides; all clients stop at teardown."""
    clients: list[TestClient] = []

    def make(**overrides: Any) -> TestClient:
        settings = service_settings.model_copy(update=overrides)
        client = TestClient(create_app(settings))
        client.__enter__()
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


def wait_for(
    client: TestClient, run_id: str, states: set[str], timeout: float = 60
) -> dict[str, Any]:
    """Poll the run detail until its state is in states."""
    deadline = time.monotonic() + timeout
    while True:
        detail = client.get(f"/api/runs/{run_id}").json()
        if detail["status"]["state"] in states:
            return detail
        assert time.monotonic() < deadline, detail["status"]
        time.sleep(0.1)


def wait_until(condition: Callable[[], bool], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.05)
