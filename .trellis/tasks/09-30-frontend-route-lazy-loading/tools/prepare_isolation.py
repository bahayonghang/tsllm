"""Export tracked baseline files and freeze the final web source without private data."""

from __future__ import annotations

import _winapi
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from acceptance_common import BASELINE, REPOSITORY, TASK, record, version, write_json


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=REPOSITORY)


def tracked(prefix: str) -> list[str]:
    return git("ls-tree", "-r", "--name-only", BASELINE, "--", prefix).decode().splitlines()


def export(root, paths):
    for name in paths:
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(git("show", f"{BASELINE}:{name}"))


def dependencies(target, source):
    """Reuse installed packages and keep all mutable tool caches local."""
    target.mkdir()
    for item in source.iterdir():
        destination = target / item.name
        if item.name == ".bin":
            shutil.copytree(item, destination)
        elif item.name.startswith(".") and item.name != ".pnpm":
            continue
        elif item.name.startswith("@"):
            destination.mkdir()
            for package in item.iterdir():
                _winapi.CreateJunction(str(package.resolve()), str(destination / package.name))
        elif item.is_dir():
            _winapi.CreateJunction(str(item.resolve()), str(destination))
    for name in (".vite", ".vite-temp", ".cache"):
        (target / name).mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("baseline", "freeze-b1"))
    parser.add_argument("--revision", default="r1")
    args = parser.parse_args()
    isolation = TASK / "isolation"
    source = isolation / "source"
    paths = [".gitignore", ".gitattributes", *tracked("web")]
    if args.action == "baseline":
        if source.exists():
            raise FileExistsError(source)
        backend = ["pyproject.toml", "uv.lock", *tracked("src")]
        export(source, backend)
        write_json(
            TASK / "evidence/snapshots/backend-source.json",
            {"baseline": BASELINE, "files": {name: record(source / name) for name in backend}},
        )
        variant, root = "B0", isolation / "B0"
        if root.exists():
            raise FileExistsError(root)
        export(root, paths)
    else:
        variant, root = "B1", isolation / f"B1-{args.revision}"
        if root.exists():
            raise FileExistsError(root)
        additions = (
            git("ls-files", "--others", "--exclude-standard", "--", "web").decode().splitlines()
        )
        allowed = {"web/src/components/RouteLoading.tsx"}
        for name in additions:
            if name not in allowed and not name.startswith("web/tests/"):
                raise RuntimeError(f"Unexpected new product file: {name}")
        paths += additions
        for name in paths:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPOSITORY / name, destination)
    files = {name: record(root / name) for name in paths}
    data = {
        "variant": variant,
        "baseline": BASELINE,
        "root": str(root),
        "source_version": version(files),
        "files": files,
        "revision": args.revision,
        "tool": record(Path(__file__)),
    }
    write_json(TASK / f"evidence/snapshots/{root.name}-source.json", data)
    dependencies(root / "web/node_modules", REPOSITORY / "web/node_modules")
    print(json.dumps({key: data[key] for key in ("variant", "root", "source_version")}))


if __name__ == "__main__":
    main()
