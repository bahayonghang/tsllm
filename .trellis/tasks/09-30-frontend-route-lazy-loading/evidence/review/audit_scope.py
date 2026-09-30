"""Check protected paths and cleanup without entering private directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
TASK = REVIEW.parents[1]
ROOT = TASK.parents[2]
PRODUCT = {
    "web/src/router.tsx",
    "web/src/components/AppLayout.tsx",
    "web/src/components/RouteLoading.tsx",
    "web/tests/LazyRouting.test.tsx",
    "web/tests/RouteResolution.test.tsx",
}
SPECS = {
    ".trellis/spec/frontend/directory-structure.md",
    ".trellis/spec/frontend/quality-guidelines.md",
    ".trellis/spec/frontend/index.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def record(path: Path) -> dict:
    stat = path.stat()
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def files(root: Path) -> dict:
    return {
        p.relative_to(ROOT).as_posix(): record(p) for p in sorted(root.rglob("*")) if p.is_file()
    }


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-cleanup", action="store_true")
    args = parser.parse_args()
    if args.output.resolve().parent != REVIEW or args.output.exists():
        raise ValueError("Use a new output file in evidence/review")
    baseline = load(TASK / "evidence/scope/preflight.json")
    failures = []
    changed = []
    missing = []
    for name, expected in baseline["tracked"].items():
        path = ROOT / name
        if not path.exists():
            missing.append(name)
        elif record(path) != expected:
            changed.append(name)
    if missing:
        failures.append({"missing_tracked": missing})
    unexpected = sorted(set(changed) - PRODUCT - SPECS)
    if unexpected:
        failures.append({"unexpected_tracked_changes": unexpected})
    protected = {}
    for key, directory in (
        ("old_assessment", ROOT / ".trellis/tasks/09-30-frontend-load-assessment"),
        ("old_dist", ROOT / "web/dist"),
    ):
        actual = files(directory)
        expected = baseline[key]
        mismatches = sorted(
            name
            for name in actual.keys() | expected.keys()
            if actual.get(name) != expected.get(name)
        )
        protected[key] = {
            "count": len(actual),
            "unchanged": not mismatches,
            "mismatches": mismatches,
        }
        if mismatches:
            failures.append({key: mismatches})
    protected["launch_unchanged"] = record(ROOT / ".claude/launch.json") == baseline["launch"]
    if not protected["launch_unchanged"]:
        failures.append({"launch": "changed"})
    protected["private_existence_only"] = {
        name: (ROOT / name).exists() for name in baseline["protected_roots_existence_only"]
    }
    if protected["private_existence_only"] != baseline["protected_roots_existence_only"]:
        failures.append({"private_roots": "existence changed"})
    staged = git("diff", "--cached", "--name-only")
    if staged:
        failures.append({"staged": staged})
    untracked = [
        x for x in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if x
    ]
    unexpected_new = [
        name
        for name in untracked
        if name not in PRODUCT
        and not name.startswith(".trellis/tasks/09-30-frontend-route-lazy-loading/")
        and name not in baseline["old_assessment"]
    ]
    if unexpected_new:
        failures.append({"unexpected_untracked": unexpected_new})
    fixture_root = TASK / "isolation/fixtures"
    fixture = load(fixture_root / "manifest.json")
    current_fixture = {}
    for area in ("configs", "cache", "runs", "source", "model-cache"):
        for file in (fixture_root / area).rglob("*"):
            if file.is_file():
                item = record(file)
                item["bytes"] = item.pop("size")
                current_fixture[file.relative_to(fixture_root).as_posix()] = item
    fixture_matches = current_fixture == fixture["files"]
    if not fixture_matches:
        failures.append({"fixture": "file set, sha256, size or mtime changed"})
    held = [
        p.relative_to(TASK).as_posix()
        for dist in (TASK / "isolation").glob("B*/web/dist")
        for p in dist.rglob("*held*")
    ]
    if held:
        failures.append({"held_assets": held})
    port_code = None
    if args.require_cleanup:
        with socket.socket() as probe:
            port_code = probe.connect_ex(("127.0.0.1", 9000))
        if port_code == 0:
            failures.append({"port_9000": "occupied"})
    checks = {}
    for label, command in (
        ("diff_check", ["git", "diff", "--check"]),
        ("cached_diff_check", ["git", "diff", "--cached", "--check"]),
    ):
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False
        )
        checks[label] = {"exit_code": result.returncode, "output": result.stdout + result.stderr}
        if result.returncode:
            failures.append({label: result.returncode})
    output = {
        "passed": not failures,
        "failures": failures,
        "baseline_sha256": record(TASK / "evidence/scope/preflight.json")["sha256"],
        "script_sha256": record(Path(__file__))["sha256"],
        "head": git("rev-parse", "HEAD").strip(),
        "branch": git("branch", "--show-current").strip(),
        "tracked_count": len(baseline["tracked"]),
        "changed_tracked": changed,
        "protected": protected,
        "staged": staged,
        "untracked_count": len(untracked),
        "unexpected_untracked": unexpected_new,
        "fixture_count": len(current_fixture),
        "fixture_unchanged": fixture_matches,
        "held_assets": held,
        "port_9000_connect_code": port_code,
        "checks": checks,
        "status": git("status", "--porcelain=v1", "--untracked-files=all"),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(
        json.dumps(
            {
                "passed": output["passed"],
                "failures": failures,
                "changed": changed,
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
