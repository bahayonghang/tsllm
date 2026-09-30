"""Prepare isolated frontend variants from an already exported baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import _winapi
from pathlib import Path
import shutil
import subprocess


def junction(target: Path, source: Path) -> None:
    if target.exists():
        raise FileExistsError(target)
    _winapi.CreateJunction(str(source.resolve()), str(target))


def dependencies(target: Path, source: Path) -> None:
    """Keep package contents shared; all tool cache directories stay local."""
    target.mkdir()
    for item in source.iterdir():
        if item.name == ".bin":
            shutil.copytree(item, target / item.name)
        elif item.name.startswith(".") and item.name != ".pnpm":
            continue
        elif item.name.startswith("@"):
            scoped = target / item.name
            scoped.mkdir()
            for package in item.iterdir():
                junction(scoped / package.name, package)
        elif item.is_dir():
            junction(target / item.name, item)
    # Vite config bundles and Vitest caches must not reach shared dependencies.
    for name in [".vite", ".vite-temp", ".cache"]:
        (target / name).mkdir(exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--variant", choices=["B0", "B1", "B2"], required=True)
    args = parser.parse_args()
    root = args.destination / args.variant
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    for name in [".gitignore", ".gitattributes"]:
        shutil.copy2(args.source / name, root / name)
    shutil.copytree(args.source / "web", root / "web")
    dependencies(root / "web/node_modules", args.dependencies)
    tool_dir = Path(__file__).resolve().parent
    shutil.copy2(tool_dir / "assessmentGraph.ts", root / "web/assessmentGraph.ts")
    config_path = root / "web/vite.config.ts"
    config = config_path.read_text(encoding="utf-8")
    config = config.replace(
        'import { defineConfig } from "vitest/config";',
        'import { defineConfig } from "vitest/config";\nimport { assessmentGraph } from "./assessmentGraph";',
    ).replace("plugins: [react()]", "plugins: [react(), assessmentGraph()]")
    config_path.write_text(config, encoding="utf-8", newline="\n")
    patch = tool_dir / f"{args.variant}.patch"
    if patch.exists() and patch.stat().st_size:
        inventory = json.loads((tool_dir / f"{args.variant}-inventory.json").read_text(encoding="utf-8"))
        for item in inventory["source_changes"]:
            path = root / item["file"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            if actual != item["before_sha256"]:
                raise ValueError(f"Patch baseline mismatch: {item['file']}")
        subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                        "apply", "--unidiff-zero", "--whitespace=error", str(patch)], cwd=root, check=True)
        for item in inventory["source_changes"]:
            path = root / item["file"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            if actual != item["after_sha256"]:
                raise ValueError(f"Applied patch differs from verified source: {item['file']}")
    print(json.dumps({"variant": args.variant, "root": str(root),
                      "shared_packages": str(args.dependencies),
                      "local_cache": str(root / "web/node_modules/.vite")}, indent=2))


if __name__ == "__main__":
    main()
