"""Apply retained source patches in memory against the historical Git commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from functools import cache
from pathlib import Path

TASK = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REPO = next(p for p in TASK.parents if (p / ".git").exists())
BASE = "e9ce26a7bd1a4ed67cd30d257354e7345c44dec1"
VARIANTS = TASK / "evidence/variants"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@cache
def baseline(path: str) -> bytes:
    assert path.startswith("web/") and ".." not in Path(path).parts
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=REPO)


def replay(variant: str) -> dict[str, bytes]:
    lines = (VARIANTS / f"{variant}.patch").read_text(encoding="utf-8").splitlines(True)
    result: dict[str, bytes] = {}
    i = 0
    while i < len(lines):
        assert lines[i].startswith("--- "), (variant, i)
        old = lines[i][4:].strip()
        path = lines[i + 1][4:].strip().removeprefix("b/")
        original = [] if old == "/dev/null" else baseline(path).decode("utf-8").splitlines(True)
        cursor = 0
        output: list[str] = []
        i += 2
        while i < len(lines) and not lines[i].startswith("--- "):
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
            assert match, (variant, path, i)
            start, removed = int(match[1]), int(match[2] or 1)
            added = int(match[4] or 1)
            start = start - 1 if removed else start
            assert start >= cursor
            output.extend(original[cursor:start])
            cursor = start
            i += 1
            old_count = new_count = 0
            while i < len(lines) and not lines[i].startswith(("@@ ", "--- ")):
                line = lines[i]
                assert line[0] in " +-", (variant, path, i)
                if line[0] in " -":
                    assert original[cursor] == line[1:], (variant, path, cursor)
                    cursor += 1
                    old_count += 1
                if line[0] in " +":
                    output.append(line[1:])
                    new_count += 1
                i += 1
            assert (old_count, new_count) == (removed, added), (variant, path)
        output.extend(original[cursor:])
        result[path] = "".join(output).encode("utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT / "source-replay-v1.json")
    output = parser.parse_args().output
    reproduced = json.loads(
        (VARIANTS / "recovery-r1/reproduction-check.json").read_text(encoding="utf-8")
    )
    prior = json.loads((VARIANTS / "reproduction-check.json").read_text(encoding="utf-8"))
    records = {row["variant"]: row for row in prior}
    records.update({row["variant"]: row for row in reproduced})
    findings = {}
    for variant in ("B0", "B1", "B2"):
        modified = replay(variant)
        inventory = json.loads((VARIANTS / f"{variant}-inventory.json").read_text(encoding="utf-8"))
        for row in inventory["source_changes"]:
            before = None if row["before_sha256"] is None else digest(baseline(row["file"]))
            assert before == row["before_sha256"], (variant, row["file"])
            assert digest(modified[row["file"]]) == row["after_sha256"], (variant, row["file"])
        modified["web/assessmentGraph.ts"] = (VARIANTS / "assessmentGraph.ts").read_bytes()
        config = (
            baseline("web/vite.config.ts")
            .decode("utf-8")
            .replace(
                'import { defineConfig } from "vitest/config";',
                'import { defineConfig } from "vitest/config";\n'
                'import { assessmentGraph } from "./assessmentGraph";',
            )
            .replace("plugins: [react()]", "plugins: [react(), assessmentGraph()]")
        )
        modified["web/vite.config.ts"] = config.encode("utf-8")
        record = records[variant]
        if variant == "B0":
            assert record["reproduced_files"] == 51 and record["mismatches"] == []
            assert record["existing_test_files_unchanged"] is True
            patches = {
                name: digest((VARIANTS / name).read_bytes())
                for name in (
                    "B0.patch",
                    "recovery-r1/before/B0.patch",
                    "recovery-r1/after/B0.patch",
                )
            }
            assert len(set(patches.values())) == 1
            findings[variant] = {
                "source_changes": len(inventory["source_changes"]),
                "source_change_hashes_checked": True,
                "patch_sha256": patches,
                "historical_summary": record,
                "files_checked": None,
                "files": [],
                "limit": "The retained B0 record has a 51-file summary only. "
                "No 51-file hash replay is claimed.",
            }
            continue
        assert record["all_equal"]
        assert record["files_compared"] == len(record["files"]) == {"B1": 53, "B2": 55}[variant]
        checked = []
        for row in record["files"]:
            path = row["file"]
            content = modified[path] if path in modified else baseline(path)
            actual = digest(content)
            assert actual == row["sha256"] == row["reproduced_sha256"], (variant, path)
            checked.append({"path": path, "sha256": actual})
        findings[variant] = {
            "source_changes": len(inventory["source_changes"]),
            "files_checked": len(checked),
            "files": checked,
        }
    result = {
        "passed": True,
        "revision": "in-memory-source-replay-v1",
        "baseline": BASE,
        "variants": findings,
        "limits": [
            "Source reconstruction only; no assets rebuilt or recompressed.",
            "Uses Git blobs and task-owned evidence only.",
        ],
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({v: row["files_checked"] for v, row in findings.items()}))


if __name__ == "__main__":
    main()
