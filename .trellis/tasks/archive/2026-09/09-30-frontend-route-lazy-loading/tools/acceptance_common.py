"""Immutable file manifests for the route-loading acceptance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
REPOSITORY = TASK.parents[2]
BASELINE = "e9ce26a7bd1a4ed67cd30d257354e7345c44dec1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict:
    stat = path.stat()
    return {
        "sha256": digest(path.read_bytes()),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def fingerprint(root: Path, areas: tuple[str, ...]) -> dict:
    return {
        path.relative_to(root).as_posix(): record(path)
        for area in areas
        for path in sorted((root / area).rglob("*"))
        if path.is_file()
    }


def version(files: dict) -> str:
    stable = {
        name: {key: item[key] for key in ("sha256", "bytes")}
        for name, item in sorted(files.items())
    }
    return digest(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def verify(files: dict, root: Path, *, mtimes: bool = False) -> None:
    for name, expected in files.items():
        actual = record(root / name)
        keys = ("sha256", "bytes", "mtime_ns") if mtimes else ("sha256", "bytes")
        if any(actual[key] != expected[key] for key in keys):
            raise RuntimeError(f"Snapshot changed: {root / name}")
