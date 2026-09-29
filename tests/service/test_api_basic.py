"""System, schema, backbones, templates, error envelope, OpenAPI, static files, imports."""

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response
from typer.testing import CliRunner

from tsllm.backbones import list_backbones
from tsllm.cli import app as cli_app
from tsllm.config.dataset import DatasetConfig
from tsllm.config.run import JobSpec, RunConfig
from tsllm.data.registry import save_dataset
from tsllm.runs.store import RunStore
from tsllm.service.app import create_app
from tsllm.service.settings import Settings

DESIGN_PATHS = {
    ("get", "/api/health"),
    ("get", "/api/system"),
    ("get", "/api/schema/run-config"),
    ("get", "/api/datasets"),
    ("get", "/api/datasets/{id}"),
    ("post", "/api/datasets/{id}/ingest"),
    ("get", "/api/datasets/{id}/series"),
    ("put", "/api/datasets/{id}/channels"),
    ("get", "/api/backbones"),
    ("get", "/api/runs"),
    ("post", "/api/runs"),
    ("get", "/api/runs/{id}"),
    ("post", "/api/runs/{id}/cancel"),
    ("get", "/api/runs/{id}/events"),
    ("get", "/api/runs/{id}/metrics"),
    ("get", "/api/runs/{id}/predictions"),
    ("get", "/api/compare"),
    ("get", "/api/run-templates"),
    ("get", "/api/run-templates/{id}"),
    ("put", "/api/run-templates/{id}"),
}


def _operations(document: dict) -> set[tuple[str, str]]:
    return {
        (method, re.sub(r"\{[^}]+\}", "{id}", path))
        for path, item in document["paths"].items()
        for method in item
    }


def _error(response: Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message", "detail"}
    assert body["error"]["code"] == code


def test_health_system_schema_backbones(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    system = client.get("/api/system").json()
    assert system["gpu_slots"] == 1 and system["cpu_slots"] == 2
    assert system["packages"]["tsllm"] is not None
    schema = client.get("/api/schema/run-config").json()
    assert set(schema) == {"run_config", "backbone_options"}
    names = [info["name"] for info in client.get("/api/backbones").json()]
    assert names == [info.name for info in list_backbones()]
    assert set(schema["backbone_options"]) == set(names)


def test_error_envelopes(
    client: TestClient,
    service_settings: Settings,
    ingested_config: DatasetConfig,
    forecast_run: Callable[..., RunConfig],
) -> None:
    _error(client.get("/api/runs/nope"), 404, "RUN_NOT_FOUND")
    _error(client.get("/api/datasets/nope"), 404, "DATASET_NOT_FOUND")
    _error(client.get("/api/run-templates/nope"), 404, "TEMPLATE_NOT_FOUND")
    _error(client.get("/api/unknown"), 404, "NOT_FOUND")

    body = forecast_run("persistence", "zero_shot").model_dump(mode="json")
    stale = ingested_config.model_copy(update={"id": "stale", "freq": ingested_config.native_freq})
    save_dataset(stale, service_settings.datasets_dir)
    _error(client.post("/api/runs", json=body | {"dataset": "stale"}), 409, "DATASET_NOT_INGESTED")

    store = RunStore(service_settings.runs_dir)
    done = store.create(JobSpec(kind="ingest", dataset=ingested_config))
    store.transition(done, "running", writer="worker")
    store.transition(done, "succeeded", writer="worker")
    _error(client.post(f"/api/runs/{done}/cancel"), 409, "INVALID_TRANSITION")

    invalid = client.post("/api/runs", json=body | {"mode": "sometimes"})
    _error(invalid, 422, "VALIDATION_ERROR")
    assert ["body", "mode"] in [error["loc"] for error in invalid.json()["error"]["detail"]]
    _error(client.post("/api/runs", json=body | {"mode": "lora"}), 422, "CAPABILITY_UNSUPPORTED")
    unknown = body | {"backbone": body["backbone"] | {"name": "nope"}}
    _error(client.post("/api/runs", json=unknown), 422, "BACKBONE_LOAD_FAILED")
    channels = [
        ch.model_copy(update={"role": "past_covariate"}) for ch in ingested_config.channels or []
    ]
    channels[0] = channels[0].model_copy(update={"role": "target"})
    covariate = ingested_config.model_copy(update={"id": "covariate", "channels": channels})
    save_dataset(covariate, service_settings.datasets_dir)
    response = client.post("/api/runs", json=body | {"dataset": "covariate"})
    _error(response, 422, "NOT_IMPLEMENTED")
    _error(client.get("/api/run-templates/bad.name"), 422, "VALIDATION_ERROR")
    # Rejected submissions create no run directory.
    assert [summary.run_id for summary in store.list()] == [done]


def test_run_templates(client: TestClient, forecast_run: Callable[..., RunConfig]) -> None:
    assert client.get("/api/run-templates").json() == []
    body = forecast_run("persistence", "zero_shot").model_dump(mode="json")
    response = client.put("/api/run-templates/my_tpl-1", json=body)
    assert response.status_code == 200 and response.json() == body
    assert client.get("/api/run-templates").json() == [{"name": "my_tpl-1"}]
    assert client.get("/api/run-templates/my_tpl-1").json() == body
    bad = client.put("/api/run-templates/x", json=body | {"extra": 1})
    _error(bad, 422, "VALIDATION_ERROR")


def test_openapi_has_design_paths(service_settings: Settings, tmp_path: Path) -> None:
    assert _operations(create_app(service_settings).openapi()) == DESIGN_PATHS
    out = tmp_path / "openapi.json"
    result = CliRunner().invoke(cli_app, ["api", "openapi", "--out", str(out)])
    assert result.exit_code == 0, result.output
    document = json.loads(out.read_text(encoding="utf-8"))
    assert _operations(document) == DESIGN_PATHS
    error = document["paths"]["/api/runs/{run_id}"]["get"]["responses"]["404"]
    assert error["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorOut")


def test_static_web_and_spa_fallback(
    make_client: Callable[..., TestClient], tmp_path: Path
) -> None:
    dist = tmp_path / "web" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>index</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("x", encoding="utf-8")
    client = make_client()
    assert client.get("/").text == "<html>index</html>"
    assert client.get("/runs/abc").text == "<html>index</html>"
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/..%2F..%2Fsecret.txt").text == "<html>index</html>"
    _error(client.get("/api/unknown"), 404, "NOT_FOUND")
    assert client.get("/api/health").json() == {"status": "ok"}


NO_TORCH_SCRIPT = """
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from httpx import Response
from tsllm.service.app import create_app
from tsllm.service.settings import Settings

root = Path(sys.argv[1])
settings = Settings(runs_dir=root / "runs", cache_dir=root / "cache", configs_dir=root / "configs")
with TestClient(create_app(settings)) as client:
    for path in ["/api/backbones", "/api/schema/run-config", "/api/system", "/api/runs"]:
        assert client.get(path).status_code == 200, path
heavy = ["torch", "transformers", "chronos", "tsfm_public", "peft", "sklearn"]
print(sorted(name for name in heavy if name in sys.modules))
"""


def test_service_does_not_import_model_libraries(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", NO_TORCH_SCRIPT, str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "[]"
