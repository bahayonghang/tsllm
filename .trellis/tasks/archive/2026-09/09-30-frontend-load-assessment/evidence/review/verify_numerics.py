"""Independently verify retained samples, asset identity, and summary arithmetic."""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

PRIMARY = {
    "cold-runs",
    "warm-runs",
    "first-form",
    "first-compare",
    "first-dataset",
    "first-forecast",
}


def stage_entries(stage):
    return stage["navigation"] + stage["resources"]


def aggregate(events):
    bodies = {}
    for event in events:
        url = urlsplit(event["name"])
        if (url.scheme, url.netloc) != ("http", "127.0.0.1:9000"):
            continue
        previous = bodies.get(event["name"])
        if previous is None or event["encodedBodySize"] > previous["encodedBodySize"]:
            bodies[event["name"]] = event
    assets = [value for url, value in bodies.items() if urlsplit(url).path.startswith("/assets/")]
    return {
        "request_entries": len(events),
        "unique_urls": len(bodies),
        "transfer_bytes_sum": sum(e["transferSize"] for e in events),
        "encoded_body_url_union": sum(e["encodedBodySize"] for e in bodies.values()),
        "decoded_body_url_union": sum(e["decodedBodySize"] for e in bodies.values()),
        "asset_url_count": len(assets),
        "asset_encoded_body_union": sum(e["encodedBodySize"] for e in assets),
        "asset_decoded_body_union": sum(e["decodedBodySize"] for e in assets),
    }


def statistics(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "count": len(values),
        "median": median,
        "min": ordered[0],
        "max": ordered[-1],
        "values": values,
    }


def equal_number(actual, expected, label):
    if expected is None:
        assert actual is None, label
    else:
        assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-7), (
            label,
            actual,
            expected,
        )


def check_statistics(actual, values, label):
    wanted = statistics(values)
    for field in ("count", "median", "min", "max"):
        equal_number(actual[field], wanted[field], label + "." + field)
    assert len(actual["values"]) == len(values), label
    for a, b in zip(actual["values"], values, strict=True):
        equal_number(a, b, label + ".values")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--supplementary-only", action="store_true")
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    inventories = {
        v: json.loads((args.variants / f"{v}-inventory.json").read_text(encoding="utf-8"))
        for v in ("B0", "B1", "B2")
    }
    assets = {v: {a["file"]: a["bytes"] for a in doc["assets"]} for v, doc in inventories.items()}
    groups = defaultdict(list)
    identities, browsers = set(), set()
    failures, raw_hashes = [], {}
    asset_entries_checked = 0
    for file in sorted(args.raw.glob("B*-*.json")):
        sample = json.loads(file.read_text(encoding="utf-8"))
        if "scenario" not in sample:
            continue
        raw_hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
        if not sample["valid"]:
            failures.append(file.name)
            continue
        identity = sample["variant"], sample["scenario"], sample["sample"]
        assert identity not in identities, ("duplicate valid sample", identity)
        identities.add(identity)
        browsers.add(sample["browser"])
        assert sample["viewport"] == {"width": 1280, "height": 900}, file.name
        assert not sample["pageErrors"], file.name
        assert not [
            r for r in sample["network"] if r.get("method") not in (None, "GET", "HEAD", "OPTIONS")
        ], file.name
        first, last = sample["stages"][0], sample["stages"][-1]
        equal_number(
            last["end"] - last["start"], sample["primaryReadyMilliseconds"], file.name + " duration"
        )
        for stage in sample["stages"]:
            equal_number(
                stage["end"] - stage["start"], stage["duration"], file.name + " stage duration"
            )
            assert stage["end"] >= stage["start"], file.name
            for chart in stage["charts"]:
                assert chart["animationFinished"] and chart["schedulerFinished"], file.name
                assert chart["width"] > 0 and chart["height"] > 0 and chart["coloredPixels"] > 0, (
                    file.name
                )
            for event in stage_entries(stage):
                path = urlsplit(event["name"]).path.lstrip("/")
                if path.startswith("assets/"):
                    assert path in assets[sample["variant"]], (
                        file.name,
                        "foreign variant asset",
                        path,
                    )
                    equal_number(
                        event["encodedBodySize"],
                        assets[sample["variant"]][path],
                        file.name + " asset length",
                    )
                    equal_number(
                        event["decodedBodySize"],
                        assets[sample["variant"]][path],
                        file.name + " decoded asset length",
                    )
                    asset_entries_checked += 1
        source, target = stage_entries(first), stage_entries(last)
        windows = {"entry": aggregate(source), "cumulative": aggregate(target)}
        if sample["scenario"] == "warm-runs":
            windows["warm"] = aggregate(target)
            windows["cumulative"] = aggregate(source + target)
        elif len(sample["stages"]) > 1:
            old_urls = {e["name"] for e in source}
            navigated = [
                e
                for e in target
                if e["startTime"] >= last["start"] and e["responseEnd"] <= last["end"]
            ]
            windows["navigation"] = aggregate(navigated)
            windows["increment"] = aggregate([e for e in navigated if e["name"] not in old_urls])
        if sample.get("preview"):
            windows["with_preview"] = aggregate(stage_entries(sample["preview"]))
        groups[f"{sample['variant']}:{sample['scenario']}"].append((file.name, sample, windows))
    assert len(browsers) == 1, browsers
    for variant in ("B0", "B1", "B2"):
        if args.supplementary_only:
            assert len(groups[f"{variant}:journey"]) >= 1, variant
        else:
            for scenario in PRIMARY:
                assert len(groups[f"{variant}:{scenario}"]) >= 5, (variant, scenario)
    calculations = 0
    for key, rows in groups.items():
        reported = summary["groups"][key]
        assert reported["files"] == [row[0] for row in rows], key
        assert reported["valid_count"] == len(rows), key
        check_statistics(
            reported["ready_ms"],
            [row[1]["stages"][-1]["duration"] for row in rows],
            key + ".ready_ms",
        )
        calculations += 1
        additional = defaultdict(list)
        for _, sample, _ in rows:
            target = sample["stages"][-1]
            additional["observer_total_ms"].append(
                target["observerCostCumulative"]["totalMilliseconds"]
                - target["observerCostAtStart"]["totalMilliseconds"]
            )
            additional["observer_document_max_predicate_ms"].append(
                target["observerCostCumulative"]["maxMilliseconds"]
            )
            durations = []
            for task in target["longTasks"]:
                left = max(target["start"], task["startTime"])
                right = min(target["end"], task["startTime"] + task["duration"])
                if right > left:
                    durations.append(right - left)
            additional["completed_long_tasks_overlapping_window"].append(len(durations))
            additional["completed_long_tasks_overlap_ms"].append(sum(durations))
            if sample.get("preview"):
                additional["preview_ready_ms"].append(
                    sample["preview"]["end"] - sample["preview"]["start"]
                )
        for metric, values in additional.items():
            check_statistics(reported[metric], values, key + "." + metric)
            calculations += 1
        for window, metrics in rows[0][2].items():
            for metric in metrics:
                check_statistics(
                    reported["windows"][window][metric],
                    [row[2][window][metric] for row in rows],
                    key + "." + window + "." + metric,
                )
                calculations += 1
    for key, values in summary["deltas_vs_B0"].items():
        variant, scenario = key.split(":")
        for name, delta in values.items():

            def value(v, scenario=scenario, name=name):
                group = summary["groups"][f"{v}:{scenario}"]
                if name == "ready_ms":
                    return group[name]["median"]
                window, metric = name.split(".")
                return group["windows"][window][metric]["median"]

            base, current = value("B0"), value(variant)
            equal_number(delta["absolute"], current - base, key + "." + name)
            equal_number(
                delta["relative_percent"],
                (current / base - 1) * 100 if base else None,
                key + "." + name,
            )
            calculations += 2
    primary_count = sum(len(rows) for key, rows in groups.items() if key.split(":")[1] in PRIMARY)
    supplementary_count = sum(
        len(rows) for key, rows in groups.items() if key.split(":")[1] not in PRIMARY
    )
    assert summary["complete_90_matrix"] == (not args.supplementary_only)
    assert summary["valid_primary_observations"] == primary_count
    assert summary["valid_supplementary_observations"] == supplementary_count
    assert sorted(x["file"] for x in summary["failures"]) == sorted(failures)
    result = {
        "passed": True,
        "primary_observations": primary_count,
        "supplementary_observations": supplementary_count,
        "failures_preserved": failures,
        "browsers": sorted(browsers),
        "groups": {key: len(rows) for key, rows in sorted(groups.items())},
        "statistics_and_delta_checks": calculations,
        "asset_entries_matched_to_variant_inventory": asset_entries_checked,
        "summary_sha256": hashlib.sha256(args.summary.read_bytes()).hexdigest(),
        "raw_sha256": raw_hashes,
        "limits": [
            "Checks measured timing and resource arithmetic; does not replace visible acceptance",
            "Does not interpret last journey stage time as total journey duration",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in {"raw_sha256", "groups"}}
        )
    )


if __name__ == "__main__":
    main()
