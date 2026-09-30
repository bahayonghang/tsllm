"""Check only declared synthetic fixtures, owned assets, and the loopback port."""

import hashlib
import json
import socket
from pathlib import Path


def main() -> None:
    task = Path(__file__).resolve().parents[2]
    metadata = json.loads((task / "task.json").read_text(encoding="utf-8"))
    experiment = Path(metadata["meta"]["experiment_root"])
    manifest = json.loads((task / "evidence/fixtures/manifest.json").read_text(encoding="utf-8"))
    root = experiment / "fixtures"
    actual = {
        path.relative_to(root).as_posix(): path
        for area in manifest["fixture_roots"].values()
        for path in (root / area).rglob("*")
        if path.is_file()
    }
    assert set(actual) == set(manifest["files"])
    for name, expected in manifest["files"].items():
        path = actual[name]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"], name
        assert path.stat().st_size == expected["bytes"], name
        assert path.stat().st_mtime_ns == expected["mtime_ns"], name
    with socket.socket() as connection:
        # A timeout socket returned WSAEWOULDBLOCK before refusal on this host.
        status = connection.connect_ex(("127.0.0.1", 9000))
    held = [
        path.relative_to(experiment).as_posix()
        for path in (experiment / "variants").glob("B*/web/dist/assets/*.assessment-held")
    ]
    models = [path for path in (experiment / "measurement/models").rglob("*") if path.is_file()]
    result = {
        "passed": status == 10061 and not held and not models,
        "fixture_files": len(actual),
        "fixture_sha256_size_mtime_unchanged": True,
        "port_9000_connect_ex": status,
        "port_9000_connection_refused": status == 10061,
        "held_asset_paths": held,
        "model_cache_file_count": len(models),
        "private_directories_opened": False,
        "visible_cleanup_receipt": "evidence/visible/cleanup-before-matrix.json",
        "visible_browser_verified_by": "Main agent receipt; checker did not operate browser",
    }
    output = Path(__file__).with_name("recovery-r1-cleanup-review.json")
    output.write_bytes((json.dumps(result, indent=2) + chr(10)).encode("utf-8"))
    print(json.dumps(result))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
