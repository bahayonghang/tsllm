"""Save clean build inventories, module graphs, and reproducible source patches."""

import argparse
import difflib
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import platform
import shutil
import zlib


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.resources: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and attributes.get("src"):
            self.resources.append(attributes["src"].lstrip("/"))
        elif tag == "link" and attributes.get("rel") in {"stylesheet", "modulepreload"}:
            self.resources.append(attributes["href"].lstrip("/"))


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
source = args.root / "source"
args.evidence.mkdir(parents=True, exist_ok=True)
all_records = []
for variant in ["B0", "B1", "B2"]:
    root = args.root / "variants" / variant
    dist = root / "web/dist"
    inventory = []
    for file in sorted(dist.rglob("*")):
        if file.is_file():
            raw = file.read_bytes()
            inventory.append({"file": file.relative_to(dist).as_posix(), "bytes": len(raw),
                              "gzip_bytes": len(gzip.compress(raw, compresslevel=9, mtime=0)),
                              "sha256": hashlib.sha256(raw).hexdigest()})
    graph_path = root / "assessment/graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    chunks = {chunk["file"]: chunk for chunk in graph["chunks"]}
    links = Links()
    links.feed((dist / "index.html").read_text(encoding="utf-8"))
    static = set(links.resources)
    todo = list(static)
    while todo:
        current = todo.pop()
        for dependency in chunks.get(current, {}).get("imports", []):
            if dependency not in static:
                static.add(dependency)
                todo.append(dependency)
    baseline_files = {file.relative_to(source).as_posix(): file for file in (source / "web").rglob("*") if file.is_file()}
    selected = dict(baseline_files)
    for folder in ["src", "tests"]:
        for file in (root / "web" / folder).rglob("*"):
            if file.is_file():
                selected[file.relative_to(root).as_posix()] = file
    patch_parts = []
    changed = []
    for name in sorted(selected):
        if name == "web/vite.config.ts":
            continue
        baseline_path = source / name
        current_path = root / name
        before = baseline_path.read_bytes() if baseline_path.is_file() else b""
        after = current_path.read_bytes() if current_path.is_file() else b""
        if before == after:
            continue
        changed.append({"file": name, "before_sha256": hashlib.sha256(before).hexdigest() if before else None,
                        "after_sha256": hashlib.sha256(after).hexdigest() if after else None})
        patch_parts.extend(difflib.unified_diff(
            before.decode("utf-8").splitlines(keepends=True),
            after.decode("utf-8").splitlines(keepends=True),
            fromfile=f"a/{name}" if before else "/dev/null",
            tofile=f"b/{name}" if after else "/dev/null",
            n=0,
        ))
    patch = args.evidence / f"{variant}.patch"
    patch.write_text("".join(patch_parts), encoding="utf-8", newline="\n")
    record = {
        "variant": variant, "baseline_commit": "e9ce26a7bd1a4ed67cd30d257354e7345c44dec1",
        "build": {"script": "tsc --noEmit && vite build", "chunkSizeWarningLimit": 2000,
                  "timing_probes": False, "output_hook": "metadata only; writes outside dist"},
        "gzip_estimate": {"python": platform.python_version(), "zlib": zlib.ZLIB_RUNTIME_VERSION,
                          "function": "gzip.compress", "compresslevel": 9, "mtime": 0,
                          "scope": "each file separately; not HTTP transfer bytes"},
        "assets": inventory,
        "total_bytes": sum(item["bytes"] for item in inventory),
        "total_gzip_bytes": sum(item["gzip_bytes"] for item in inventory),
        "html_resources": links.resources,
        "bootstrap_static_closure": sorted(static),
        "bootstrap_note": "Static HTML closure only; excludes initial lazy route until browser measurement",
        "source_changes": changed,
        "unchanged_locks": {name: digest(root / "web" / name) == digest(source / "web" / name)
                            for name in ["package.json", "pnpm-lock.yaml", "openapi.json", "src/api/schema.d.ts"]},
        "patch_sha256": digest(patch),
        "graph_file": f"{variant}-graph.json",
        "module_attribution_note": "Rolldown renderedLength is module metadata, not compressed bytes or measured transfer attribution",
    }
    (args.evidence / f"{variant}-inventory.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    shutil.copy2(graph_path, args.evidence / f"{variant}-graph.json")
    all_records.append({"variant": variant, "assets": len(inventory), "total_bytes": record["total_bytes"],
                        "total_gzip_bytes": record["total_gzip_bytes"], "source_files_changed": len(changed),
                        "locks_unchanged": all(record["unchanged_locks"].values())})
print(json.dumps(all_records, indent=2))
