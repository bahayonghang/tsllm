"""Dataset list, detail, series, and channel dictionary routes."""

from datetime import datetime

from fastapi.testclient import TestClient

from tsllm.service.settings import Settings


def test_list_and_detail(client: TestClient) -> None:
    [item] = client.get("/api/datasets").json()
    assert item["id"] == "synthetic" and item["status"] == "fresh"
    detail = client.get("/api/datasets/synthetic").json()
    assert detail["config_hash"] == item["config_hash"]
    assert detail["meta"]["channel_names"] == ["late", "operating", "signal"]


def test_series_buckets(client: TestClient) -> None:
    full = client.get("/api/datasets/synthetic/series", params={"max_points": 100}).json()
    assert 0 < len(full["time"]) <= 100 and full["every"] != "1min"
    assert set(full["values"]) == {"late", "operating", "signal"}
    assert all(len(values) == len(full["time"]) for values in full["values"].values())
    assert full["segments"] and set(full["split_boundaries"]) == {"val", "cal", "test"}

    start, end = "2024-01-01T01:00:00", "2024-01-01T02:59:00"
    part = client.get(
        "/api/datasets/synthetic/series",
        params={"channels": ["signal"], "start": start, "end": end, "max_points": 20000},
    ).json()
    assert list(part["values"]) == ["signal"] and part["every"] == "1min"
    times = [datetime.fromisoformat(t) for t in part["time"]]
    assert len(times) == 120
    assert times[0] == datetime.fromisoformat(start) and times[-1] == datetime.fromisoformat(end)

    bad = client.get("/api/datasets/synthetic/series", params={"channels": ["nope"]})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "CHANNEL_INVALID"
    too_many = client.get("/api/datasets/synthetic/series", params={"max_points": 20001})
    assert too_many.json()["error"]["code"] == "VALIDATION_ERROR"


def test_channel_dictionary_update(client: TestClient, service_settings: Settings) -> None:
    before = client.get("/api/datasets/synthetic").json()
    channels = before["config"]["channels"]
    for channel in channels:
        channel["unit"] = "°C"
        channel["description"] = "温度"
    response = client.put("/api/datasets/synthetic/channels", json={"channels": channels[::-1]})
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["config_hash"] == before["config_hash"] and body["needs_ingest"] is False
    assert [c["name"] for c in body["config"]["channels"]] == ["late", "operating", "signal"]
    text = (service_settings.datasets_dir / "synthetic.yaml").read_text(encoding="utf-8")
    assert "温度" in text and "\\" not in text

    channels[0]["role"] = "ignore"
    body = client.put("/api/datasets/synthetic/channels", json={"channels": channels}).json()
    assert body["config_hash"] != before["config_hash"] and body["needs_ingest"] is True
    assert client.get("/api/datasets/synthetic").json()["status"] == "stale"

    renamed = [dict(channels[0], name="other"), *channels[1:]]
    response = client.put("/api/datasets/synthetic/channels", json={"channels": renamed})
    assert response.status_code == 422 and response.json()["error"]["code"] == "CHANNEL_INVALID"
    dropped = client.put("/api/datasets/synthetic/channels", json={"channels": channels[1:]})
    assert dropped.json()["error"]["code"] == "CHANNEL_INVALID"
