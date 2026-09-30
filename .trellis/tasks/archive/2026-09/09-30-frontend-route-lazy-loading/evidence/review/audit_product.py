"""Check the frozen source, unchanged contracts, and exact formal gate commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
TASK = REVIEW.parents[1]
ROOT = TASK.parents[2]
BASELINE = "e9ce26a7bd1a4ed67cd30d257354e7345c44dec1"
EXPECTED = {
    "web/src/router.tsx",
    "web/src/components/AppLayout.tsx",
    "web/src/components/RouteLoading.tsx",
    "web/tests/LazyRouting.test.tsx",
    "web/tests/RouteResolution.test.tsx",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def version(files: dict) -> str:
    stable = {
        name: {key: row[key] for key in ("sha256", "bytes")} for name, row in sorted(files.items())
    }
    return sha(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().parent != REVIEW or args.output.exists():
        raise ValueError("Use a new output file in evidence/review")
    experiment = read(args.experiment)
    failures = []
    b0 = experiment["variants"]["B0"]["source"]
    b1 = experiment["variants"]["B1"]["source"]
    for name, row in b0["files"].items():
        result = subprocess.run(
            ["git", "show", BASELINE + ":" + name], cwd=ROOT, capture_output=True, check=True
        )
        if sha(result.stdout) != row["sha256"]:
            failures.append("B0 differs from fixed Git blob: " + name)
    differences = []
    for name in b0["files"].keys() | b1["files"].keys():
        old, new = b0["files"].get(name), b1["files"].get(name)
        if old is None or new is None or old["sha256"] != new["sha256"]:
            differences.append(name)
    if set(differences) != EXPECTED:
        failures.append("Unexpected B0/B1 source difference set")
    for name, row in b1["files"].items():
        body = (ROOT / name).read_bytes()
        if sha(body) != row["sha256"] or len(body) != row["bytes"]:
            failures.append("Working source differs from frozen B1: " + name)
    package = read(ROOT / "web/package.json")
    gates = []
    for variant, stem in (("B0", "B0"), ("B1", "B1-r1")):
        frozen = experiment["variants"][variant]
        if version(frozen["source"]["files"]) != frozen["source"]["source_version"]:
            failures.append(variant + " source version calculation")
        if version(frozen["build"]["files"]) != frozen["build"]["dist_version"]:
            failures.append(variant + " dist version calculation")
        for gate in ("check", "test", "build"):
            path = TASK / f"evidence/gates/{stem}-{gate}-1.json"
            record = read(path)
            if record["exit_code"] != 0:
                failures.append(str(path) + " nonzero exit")
            if record["source_version"] != frozen["source"]["source_version"]:
                failures.append(str(path) + " source identity")
            if record["command"] != package["scripts"][gate]:
                failures.append(str(path) + " package script mismatch")
            commands = [
                Path(component["argv"][0]).stem + " " + " ".join(component["argv"][1:])
                for component in record["components"]
            ]
            if " && ".join(commands) != package["scripts"][gate]:
                failures.append(str(path) + " component command mismatch")
            if any(component["exit_code"] for component in record["components"]):
                failures.append(str(path) + " component failure")
            log = path.parent / record["log"]
            text = re.sub(r"\x1b\[[0-9;]*m", "", log.read_text(encoding="utf-8"))
            test_count = None
            if gate == "test":
                match = re.search(r"Tests\s+(\d+) passed", text)
                test_count = int(match[1]) if match else None
                if test_count != (27 if variant == "B0" else 41):
                    failures.append(str(path) + " full test count")
            gates.append(
                {
                    "record": str(path),
                    "sha256": sha(path.read_bytes()),
                    "log": str(log),
                    "log_sha256": sha(log.read_bytes()),
                    "source_version": record["source_version"],
                    "command": record["command"],
                    "exit_code": record["exit_code"],
                    "test_count": test_count,
                }
            )
    output = {
        "passed": not failures,
        "failures": failures,
        "experiment_sha256": sha(args.experiment.read_bytes()),
        "script_sha256": sha(Path(__file__).read_bytes()),
        "source_differences": sorted(differences),
        "b0_source_count": len(b0["files"]),
        "b1_source_count": len(b1["files"]),
        "preserved_original_test_files": sorted(
            name for name in b0["files"] if name.startswith("web/tests/")
        ),
        "gates": gates,
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "passed": output["passed"],
                "failures": failures,
                "gates": len(gates),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
