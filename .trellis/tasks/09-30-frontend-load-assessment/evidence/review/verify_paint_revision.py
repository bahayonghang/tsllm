"""Verify paint coverage and instrument identity in the replacement matrix."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parents[1] / "measurement"
    expected_hashes = {
        name: hashlib.sha256((scripts / name).read_bytes()).hexdigest()
        for name in ("browser_probe.mjs", "measure.mjs")
    }
    statuses: Counter[str] = Counter()
    coverage: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    snapshot_counts: Counter[str] = Counter()
    waits: list[float] = []
    gaps: list[str] = []
    hashes: dict[str, str] = {}
    recovered = 0
    after_ready = 0
    documents = 0
    for folder in ("raw", "journey"):
        sidecar = read(args.measurement_root / f"{folder}-instrumentation.json")
        assert sidecar["revision"] == "paint-collection-r1"
        assert sidecar["scripts"] == expected_hashes
        for path in sorted((args.measurement_root / folder).glob("B*-*.json")):
            sample = read(path)
            assert sample["valid"], path.name
            assert sample["instrumentation"] == sidecar, path.name
            assert "paint" in sample["capabilities"]["supportedEntryTypes"]
            counts[folder] += 1
            hashes[f"{folder}/{path.name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
            stages = [*sample["stages"]]
            snapshot_counts[f"{folder}_stages"] += len(stages)
            if sample.get("preview"):
                stages.append(sample["preview"])
                snapshot_counts[f"{folder}_preview"] += 1
            by_document: dict[float, float] = {}
            for stage in stages:
                label = f"{folder}/{path.name}:{stage['id']}"
                collection = stage["paintCollection"]
                assert collection["timeoutMs"] == 1000, label
                assert collection["scope"] == "document", label
                assert collection["readyEndpoint"] == stage["end"], label
                assert collection["collectedAt"] >= collection["startedAt"] >= stage["end"]
                assert math.isclose(
                    collection["waitMs"],
                    collection["collectedAt"] - collection["startedAt"],
                    abs_tol=1e-7,
                ), label
                assert math.isclose(
                    stage["duration"], stage["end"] - stage["start"], abs_tol=1e-7
                ), label
                assert all(item in stage["paint"] for item in stage["paintAtReady"]), label
                fcp = [item for item in stage["paint"] if item["name"] == "first-contentful-paint"]
                statuses[collection["status"]] += 1
                waits.append(collection["waitMs"])
                if collection["status"] != "observed" or collection.get("error") or len(fcp) != 1:
                    gaps.append(label)
                    continue
                native = fcp[0]
                assert native["entryType"] == "paint" and native["duration"] == 0, label
                assert 0 <= native["startTime"] <= collection["collectedAt"], label
                origin = stage["timeOrigin"]
                if origin in by_document:
                    assert by_document[origin] == native["startTime"], label
                by_document[origin] = native["startTime"]
                recovered += not any(
                    item["name"] == "first-contentful-paint" for item in stage["paintAtReady"]
                )
                after_ready += native["startTime"] > stage["end"]
            documents += len(by_document)
            if sample["scenario"] in {"cold-runs", "warm-runs"}:
                target = sample["stages"][-1]
                if target["paintCollection"]["status"] == "observed":
                    coverage[f"{sample['variant']}:{sample['scenario']}"] += 1
    assert counts == {"raw": 90, "journey": 3}, counts
    assert len(coverage) == 6 and all(count == 5 for count in coverage.values()), coverage
    result = {
        "passed": not gaps,
        "observations": dict(counts),
        "document_groups": documents,
        "snapshot_counts": dict(snapshot_counts),
        "paint_status_counts": dict(statuses),
        "cold_warm_fcp_coverage": dict(coverage),
        "fcp_missing_at_ready_but_collected_later": recovered,
        "fcp_native_timestamp_after_ready": after_ready,
        "paint_collection_wait_ms_range": [min(waits), max(waits)],
        "coverage_gaps": gaps,
        "instrument_scripts_sha256": expected_hashes,
        "raw_sha256": hashes,
        "limits": [
            "Checks retained native records and metadata; does not run a browser",
            "Readiness immutability is also covered by the collector regression tests",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in result.items() if key != "raw_sha256"}))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
