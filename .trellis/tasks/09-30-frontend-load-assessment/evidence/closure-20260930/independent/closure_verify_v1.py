"""Recheck retained assessment evidence without a build or an external workspace."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path
from statistics import median

TASK = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REPO = next(p for p in TASK.parents if (p / ".git").exists())
BASE = "e9ce26a7bd1a4ed67cd30d257354e7345c44dec1"
HISTORICAL_CRLF_PATHS = {
    ".trellis/spec/guides/code-reuse-thinking-guide.md",
    ".trellis/spec/guides/cross-layer-thinking-guide.md",
    ".trellis/spec/guides/index.md",
    ".trellis/tasks/archive/2026-09/00-bootstrap-guidelines/task.json",
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(actual, expected, label: str) -> int:
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), label
        return sum(compare(actual[k], v, label + "." + k) for k, v in expected.items())
    if isinstance(expected, list):
        assert len(actual) == len(expected), label
        return sum(compare(a, b, label) for a, b in zip(actual, expected, strict=True))
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-7), label
    else:
        assert actual == expected, label
    return 1


def stat(values: list) -> dict:
    present = [x for x in values if x is not None]
    return {
        "n": len(present),
        "observations": len(values),
        "median": median(present) if present else None,
        "min": min(present) if present else None,
        "max": max(present) if present else None,
        "values": values,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT / "closure-evidence-v1.json")
    output = parser.parse_args().output
    report_script = TASK / "evidence/report/recompute_report.py"
    spec = importlib.util.spec_from_file_location("retained_report", report_script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = read(TASK / "evidence/report/recomputed.json")
    assert report["script_sha256"] == sha(report_script)
    assert report["revision"] == "recovery-r1" and report["baseline_commit"] == BASE
    measured = TASK / "evidence/measurement/recovery-r1"
    checked = 0
    samples = {}
    for folder in ("raw", "journey"):
        for path in sorted((measured / folder).glob("B*-*.json")):
            item = read(path)
            assert item["valid"] and item["attempt"] == 1, path.name
            assert sha(path) == report["raw_sha256"][f"{folder}/{path.name}"], path.name
            row = module.sample_values(item)
            row.update(file=path.name, sample=item["sample"])
            samples.setdefault(f"{item['variant']}:{item['scenario']}", []).append(row)
    assert len(samples) == 21 and sum(map(len, samples.values())) == 93
    for key, rows in samples.items():
        assert len(rows) == (1 if key.endswith(":journey") else 5), key
        expected = report["groups"][key]
        checked += compare(rows, expected["observations"], key)
        for metric in expected["metrics"]:
            checked += compare(
                stat([r["metrics"][metric] for r in rows]),
                expected["metrics"][metric],
                key + "." + metric,
            )
        for window, metrics in expected["windows"].items():
            for metric, values in metrics.items():
                checked += compare(
                    stat([r["windows"][window][metric] for r in rows]),
                    values,
                    key + "." + window + "." + metric,
                )
    for pair, comparisons in report["comparisons"].items():
        variant, base = pair.split("_vs_")
        for scenario, values in comparisons.items():
            groups = report["groups"]
            current, previous = groups[f"{variant}:{scenario}"], groups[f"{base}:{scenario}"]
            for metric, change in values["metrics"].items():
                checked += compare(
                    module.delta(
                        current["metrics"][metric]["median"], previous["metrics"][metric]["median"]
                    ),
                    change,
                    pair + "." + scenario + "." + metric,
                )
            for window, metrics in values["windows"].items():
                for metric, change in metrics.items():
                    checked += compare(
                        module.delta(
                            current["windows"][window][metric]["median"],
                            previous["windows"][window][metric]["median"],
                        ),
                        change,
                        pair + "." + scenario + "." + window + "." + metric,
                    )
    inventories = TASK / "evidence/variants"
    integrity = read(TASK / "evidence/review/recovery-r1-variant-integrity.json")
    builds = {}
    gates = []
    for old in integrity["variants"]:
        variant = old["variant"]
        inventory = read(inventories / f"{variant}-inventory.json")
        assert report["builds"][variant] == inventory
        assert inventory["baseline_commit"] == BASE
        assert inventory["patch_sha256"] == sha(inventories / f"{variant}.patch")
        for suffix in ("patch", "inventory.json", "graph.json"):
            name = f"{variant}.{suffix}" if suffix == "patch" else f"{variant}-{suffix}"
            assert sha(inventories / name) == sha(inventories / "recovery-r1/after" / name)
        assets = {x["file"]: x for x in inventory["assets"]}
        raw, gzip = (
            sum(x["bytes"] for x in assets.values()),
            sum(x["gzip_bytes"] for x in assets.values()),
        )
        assert raw == inventory["total_bytes"] == old["bytes"]
        assert gzip == inventory["total_gzip_bytes"] == old["gzip_estimate_bytes"]
        graph = read(inventories / f"{variant}-graph.json")["chunks"]
        assert {c["file"] for c in graph} == {p for p in assets if p.endswith(".js")}
        for chunk in graph:
            assert set(chunk["imports"] + chunk["dynamicImports"]) <= assets.keys()
        for gate, receipt in old["latest_gates"].items():
            stem = f"{variant}-{gate}-{receipt['attempt']}"
            log = TASK / "evidence/variant-gates" / (stem + ".txt")
            result = read(log.with_suffix(".json"))
            assert result["exit_code"] == 0
            assert sha(log) == receipt["log_sha256"], stem
            gates.append({"gate": stem, "sha256": sha(log), "exit_code": 0})
        builds[variant] = {"files": len(assets), "raw_bytes": raw, "gzip_sum_bytes": gzip}
    for name in ("browser_probe.mjs", "measure.mjs"):
        assert sha(TASK / "evidence/measurement" / name) == sha(
            measured / "instrument/after" / name
        )
    historical = read(TASK / "evidence/scope/baseline-tracked-sha256.json")
    forbidden = {"data", "ref", "runs", "cache"}
    assert all(Path(p).parts[0] not in forbidden for p in historical)
    batch = "".join(f"{BASE}:{p}\n" for p in historical)
    process = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=REPO,
        input=batch.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    payload, cursor, mismatches = process.stdout, 0, []
    exact_blob_matches = 0
    historical_crlf = {}
    for path, expected in historical.items():
        end = payload.index(b"\n", cursor)
        header = payload[cursor:end].split()
        assert len(header) == 3 and header[1] == b"blob", path
        size = int(header[2])
        blob = payload[end + 1 : end + 1 + size]
        blob_sha256 = hashlib.sha256(blob).hexdigest()
        if blob_sha256 == expected:
            exact_blob_matches += 1
        elif path in HISTORICAL_CRLF_PATHS:
            assert b"\r" not in blob, ("expected LF-only Git blob", path)
            crlf_worktree = blob.replace(b"\n", b"\r\n")
            reconstructed_sha256 = hashlib.sha256(crlf_worktree).hexdigest()
            assert reconstructed_sha256 == expected, ("explicit CRLF proof failed", path)
            historical_crlf[path] = {
                "git_blob_sha256": blob_sha256,
                "git_blob_size": len(blob),
                "historical_worktree_sha256": expected,
                "reconstructed_crlf_sha256": reconstructed_sha256,
                "reconstructed_crlf_size": len(crlf_worktree),
                "converted_lf_count": blob.count(b"\n"),
                "conversion": "LF-only Git blob, each LF replaced with CRLF",
                "historical_sha256_matches_reconstruction": True,
            }
        else:
            mismatches.append(path)
        cursor = end + size + 2
    assert not mismatches, ("historical Git baseline", mismatches)
    assert len(historical) == 289 and exact_blob_matches == 285
    assert set(historical_crlf) == HISTORICAL_CRLF_PATHS
    preflight = read(TASK / "evidence/closure-20260930/preflight.json")
    protection = {}
    for group in ("tracked_files", "protected_files"):
        changed = [
            row["path"]
            for row in preflight[group]
            if sha(REPO / row["path"]) != row["sha256"]
            or (REPO / row["path"]).stat().st_size != row["size"]
        ]
        protection[group] = {"count": len(preflight[group]), "changed": changed}
        assert not changed, (group, changed)
    high = read(measured / "raw/B2-first-forecast-s3-a1.json")
    assert round(high["primaryReadyMilliseconds"], 1) == 2439.7
    result = {
        "revision": "closure-evidence-v1",
        "passed": True,
        "read_only_import": str(report_script.relative_to(TASK)).replace("\\", "/"),
        "import_sha256": sha(report_script),
        "value_comparisons": checked,
        "main_observations": 90,
        "journeys": 3,
        "groups": 21,
        "builds": builds,
        "gates": gates,
        "historical_git_blob_hashes_checked": len(historical),
        "historical_exact_git_blob_matches": exact_blob_matches,
        "historical_explicit_crlf_worktree_proofs": historical_crlf,
        "historical_baseline": BASE,
        "current_protection": protection,
        "retained_high_value_ms": high["primaryReadyMilliseconds"],
        "limits": [
            "Imports only retained pure report functions; never calls report main.",
            "Re-sums retained per-asset gzip sizes; does not recompress missing artifacts.",
            "Reuses hash-bound build, lint, TypeScript and visible acceptance evidence.",
            "No new browser, server, benchmark, dependency operation or private-root read.",
        ],
    }
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
