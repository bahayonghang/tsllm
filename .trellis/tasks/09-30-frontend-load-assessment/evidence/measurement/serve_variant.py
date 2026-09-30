"""Serve one fixed variant with isolated synthetic roots on port 9000."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--variant-root", required=True, type=Path)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    source = args.source_root.resolve(strict=True)
    variant = args.variant_root.resolve(strict=True)
    fixture = args.fixture_root.resolve(strict=True)
    model_cache = args.model_cache.resolve()
    assert (source / "src" / "tsllm" / "service" / "app.py").is_file()
    assert (variant / "web" / "dist" / "index.html").is_file()
    assert variant != fixture and fixture not in variant.parents and variant not in fixture.parents
    for name in ("runs", "cache", "configs"):
        assert (fixture / name).is_dir()
    statuses = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (fixture / "runs").glob("*/status.json")
    ]
    assert len(statuses) == 5 and all(
        item["state"] in {"succeeded", "failed", "cancelled", "interrupted"} for item in statuses
    )
    model_cache.mkdir(parents=True, exist_ok=True)
    assert not any(path.is_file() for path in model_cache.rglob("*")), "Model cache must be empty"
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "DO_NOT_TRACK": "1",
            "HF_HOME": str(model_cache / "hf"),
            "HUGGINGFACE_HUB_CACHE": str(model_cache / "hf" / "hub"),
            "TORCH_HOME": str(model_cache / "torch"),
            "XDG_CACHE_HOME": str(model_cache / "xdg"),
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
            "http_proxy": "http://127.0.0.1:9",
            "https_proxy": "http://127.0.0.1:9",
            "all_proxy": "http://127.0.0.1:9",
            "no_proxy": "127.0.0.1,localhost",
            "TSLLM_RUNS_DIR": str(fixture / "runs"),
            "TSLLM_CACHE_DIR": str(fixture / "cache"),
            "TSLLM_CONFIGS_DIR": str(fixture / "configs"),
        }
    )
    sys.path.insert(0, str(source / "src"))
    from tsllm.service.app import create_app
    from tsllm.service.settings import Settings

    settings = Settings(
        runs_dir=fixture / "runs",
        cache_dir=fixture / "cache",
        configs_dir=fixture / "configs",
        web_dist=variant / "web" / "dist",
    )
    app = create_app(settings)
    assert "torch" not in sys.modules
    if args.check_only:
        print(
            json.dumps(
                {
                    "settings_valid": True,
                    "terminal_jobs": len(statuses),
                    "torch_imported": False,
                    "port": 9000,
                }
            )
        )
        return
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", 9000))
        except OSError:
            raise SystemExit("Port 9000 is occupied; no process was stopped") from None
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
