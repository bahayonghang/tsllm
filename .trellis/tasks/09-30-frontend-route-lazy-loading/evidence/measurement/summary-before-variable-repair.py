"""Recompute URL accounting and sample statistics from retained raw observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

SCENARIOS = (
    "cold-runs",
    "warm-runs",
    "first-form",
    "first-compare",
    "first-dataset",
    "first-forecast",
)


def stats(values: list[float]) -> dict:
    return {
        "count": len(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "values": values,
    }


def entries(stage: dict) -> list[dict]:
    return stage["navigation"] + stage["resources"]


def resource_summary(values: list[dict]) -> dict:
    unique: dict[str, dict] = {}
    for entry in values:
        if not entry["name"].startswith("http://127.0.0.1:9000/"):
            continue
        old = unique.get(entry["name"])
        if old is None or entry["encodedBodySize"] > old["encodedBodySize"]:
            unique[entry["name"]] = entry
    assets = [
        entry for entry in unique.values() if urlsplit(entry["name"]).path.startswith("/assets/")
    ]
    return {
        "request_entries": len(values),
        "unique_urls": len(unique),
        "transfer_bytes_sum": sum(entry["transferSize"] for entry in values),
        "encoded_body_url_union": sum(entry["encodedBodySize"] for entry in unique.values()),
        "decoded_body_url_union": sum(entry["decodedBodySize"] for entry in unique.values()),
        "asset_url_count": len(assets),
        "asset_encoded_body_union": sum(entry["encodedBodySize"] for entry in assets),
        "asset_decoded_body_union": sum(entry["decodedBodySize"] for entry in assets),
    }


def sample_values(item: dict) -> dict:
    source, target = item["stages"][0], item["stages"][-1]
    source_entries = entries(source)
    target_entries = entries(target)
    windows = {
        "entry": resource_summary(source_entries),
        "cumulative": resource_summary(target_entries),
    }
    if item["scenario"] == "warm-runs":
        windows["warm"] = resource_summary(target_entries)
        windows["cumulative"] = resource_summary(source_entries + target_entries)
    elif len(item["stages"]) > 1:
        source_urls = {entry["name"] for entry in source_entries}
        navigation = [
            entry
            for entry in target_entries
            if target["start"] <= entry["startTime"] and entry["responseEnd"] <= target["end"]
        ]
        windows["navigation"] = resource_summary(navigation)
        windows["increment"] = resource_summary(
            [entry for entry in navigation if entry["name"] not in source_urls]
        )
    if item.get("preview"):
        windows["with_preview"] = resource_summary(entries(item["preview"]))
    out = {"ready_ms": item["primaryReadyMilliseconds"], "windows": windows}
    if item.get("preview"):
        out["preview_ready_ms"] = item["preview"]["duration"]
    out["observer_total_ms"] = (
        target["observerCostCumulative"]["totalMilliseconds"]
        - target["observerCostAtStart"]["totalMilliseconds"]
    )
    out["observer_document_max_predicate_ms"] = target["observerCostCumulative"]["maxMilliseconds"]
    overlaps = [
        max(
            0,
            min(task["startTime"] + task["duration"], target["end"])
            - max(task["startTime"], target["start"]),
        )
        for task in target["longTasks"]
    ]
    out["completed_long_tasks_overlapping_window"] = sum(value > 0 for value in overlaps)
    out["completed_long_tasks_overlap_ms"] = sum(overlaps)
    out["cdp_encoded_data_length"] = sum(
        request.get("encodedDataLength", 0) for request in item["network"]
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    experiment_bytes = args.experiment.read_bytes()
    experiment = json.loads(experiment_bytes)
    experiment_hash = hashlib.sha256(experiment_bytes).hexdigest()
    identity = experiment["measurement_identity"]
    sidecar = args.input.with_name(args.input.name + "-instrumentation.json")
    assert json.loads(sidecar.read_text(encoding="utf-8")) == identity
    groups: dict[tuple[str, str], list[tuple[str, dict]]] = defaultdict(list)
    failures = []
    cache_counts: Counter = Counter()
    headers = []
    seen = set()
    browsers = set()
    for path in sorted(args.input.glob("B*-*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if "scenario" not in item:
            continue
        assert item["instrumentation"] == identity, f"Mixed instrument: {path}"
        assert item["experiment_manifest_sha256"] == experiment_hash, f"Mixed experiment: {path}"
        assert item["product"] == identity["variants"][item["variant"]], f"Mixed product: {path}"
        if not item["valid"]:
            failures.append(
                {
                    "file": path.name,
                    "variant": item["variant"],
                    "scenario": item["scenario"],
                    "sample": item["sample"],
                    "error": item.get("error"),
                }
            )
            continue
        identity = (item["variant"], item["scenario"], item["sample"])
        assert identity not in seen, (
            f"Multiple valid attempts for {identity}; do not silently select a preferred run"
        )
        seen.add(identity)
        groups[(item["variant"], item["scenario"])].append((path.name, item))
        browsers.add(item["browser"])
        for request in item["network"]:
            if not request.get("url", "").startswith("http://127.0.0.1:9000/"):
                continue
            cache_counts[request["cacheClassification"]] += 1
            if "/assets/" in request["url"]:
                headers.append(
                    {
                        "file": path.name,
                        "url": request["url"],
                        "status": request.get("status"),
                        "network_status": request.get("networkStatusCode"),
                        "cache_class": request["cacheClassification"],
                        "headers": request.get(
                            "networkResponseHeaders", request.get("responseHeaders", {})
                        ),
                    }
                )
    complete = all(
        len(groups[(variant, scenario)]) == 5 for variant in ("B0", "B1") for scenario in SCENARIOS
    )
    summary = {
        "schema_version": 1,
        "measurement_identity": identity,
        "summary_role": (
            "Implementation-side descriptive summary; "
            "independent review must recompute raw records"
        ),
        "complete_60_matrix": complete,
        "valid_primary_observations": sum(
            len(items) for (variant, scenario), items in groups.items() if scenario in SCENARIOS
        ),
        "valid_supplementary_observations": sum(
            len(items) for (variant, scenario), items in groups.items() if scenario not in SCENARIOS
        ),
        "failures": failures,
        "browser_versions": sorted(browsers),
        "cache_classification_counts": dict(cache_counts),
        "limits": [
            "Headless installed browser on loopback; not visible acceptance or real phone/network",
            "Cold means browser HTTP cache only; OS, process and code caches are not claimed cold",
            "Readiness includes identical external observer cost and two stable animation frames",
            "Long tasks include observer and browser work and are not assigned to a package",
            "Resource Timing transferSize is browser-reported transfer; "
            "does not measure TCP/IP packet overhead",
            "Largest observed body per full URL; every request remains in transfer sums",
            "Warm is reload in same page/context after verified cold entry; "
            "actual cache outcome remains observed",
            "FCP and navigation timing describe document loads; "
            "SPA navigation uses browser click-to-ready timing",
        ],
        "groups": {},
    }
    for (variant, scenario), samples in sorted(groups.items()):
        if not samples:
            continue
        values = [sample_values(item) for _, item in samples]
        group = {
            "files": [name for name, _ in samples],
            "valid_count": len(samples),
            "ready_ms": stats([item["ready_ms"] for item in values]),
            "observer_total_ms": stats([item["observer_total_ms"] for item in values]),
            "observer_document_max_predicate_ms": stats(
                [item["observer_document_max_predicate_ms"] for item in values]
            ),
            "completed_long_tasks_overlapping_window": stats(
                [item["completed_long_tasks_overlapping_window"] for item in values]
            ),
            "completed_long_tasks_overlap_ms": stats(
                [item["completed_long_tasks_overlap_ms"] for item in values]
            ),
            "ready_definition": "Last system navigation only; not full journey elapsed time"
            if scenario == "journey"
            else "Primary scenario readiness in browser time",
            "windows": {},
        }
        if "preview_ready_ms" in values[0]:
            group["preview_ready_ms"] = stats([item["preview_ready_ms"] for item in values])
        group["cdp_encoded_data_length"] = stats(
            [item["cdp_encoded_data_length"] for item in values]
        )
        primary_stages = [item["stages"][-1] for _, item in samples]
        group["paint_status_counts"] = dict(
            Counter(stage["paintCollection"]["status"] for stage in primary_stages)
        )
        fcps = [
            paint["startTime"]
            for stage in primary_stages
            for paint in stage["paint"]
            if paint["name"] == "first-contentful-paint"
        ]
        group["native_document_fcp_ms"] = stats(fcps) if fcps else None
        group["fcp_scope"] = "Document paint; not a SPA-navigation duration"
        url_union = {}
        for _, item in samples:
            for stage in item["stages"]:
                for entry in entries(stage):
                    name = entry["name"]
                    if not name.startswith("http://127.0.0.1:9000/"):
                        continue
                    old = url_union.get(name)
                    if old is None or entry["encodedBodySize"] > old["encodedBodySize"]:
                        url_union[name] = {
                            key: entry[key] for key in ("encodedBodySize", "decodedBodySize")
                        }
        assets = experiment["variants"][variant]["build"]["files"]
        for name, value in url_union.items():
            asset = assets.get(urlsplit(name).path.lstrip("/"))
            if asset is not None:
                value["offline_gzip_bytes"] = asset["gzip_bytes"]
                value["asset_sha256"] = asset["sha256"]
        group["full_url_union_across_samples"] = url_union
        group["offline_asset_gzip_url_union_bytes"] = sum(
            item.get("offline_gzip_bytes", 0) for item in url_union.values()
        )
        for window in values[0]["windows"]:
            group["windows"][window] = {
                metric: stats([item["windows"][window][metric] for item in values])
                for metric in values[0]["windows"][window]
            }
        summary["groups"][variant + ":" + scenario] = group
    summary["deltas_vs_B0"] = {}
    for variant in ("B1",):
        for scenario in (*SCENARIOS, "journey"):
            key = variant + ":" + scenario
            baseline = summary["groups"].get("B0:" + scenario)
            current = summary["groups"].get(key)
            if baseline is None or current is None:
                continue
            deltas = {}
            measures = [("ready_ms", baseline["ready_ms"]["median"], current["ready_ms"]["median"])]
            for window in current["windows"]:
                for metric in current["windows"][window]:
                    measures.append(
                        (
                            window + "." + metric,
                            baseline["windows"][window][metric]["median"],
                            current["windows"][window][metric]["median"],
                        )
                    )
            for name, base, value in measures:
                deltas[name] = {
                    "absolute": value - base,
                    "relative_percent": (value - base) / base * 100 if base else None,
                }
            summary["deltas_vs_B0"][key] = deltas
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    with args.output.with_name(args.output.stem + "-asset-headers.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(json.dumps(headers, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "complete_60_matrix",
                    "valid_primary_observations",
                    "valid_supplementary_observations",
                    "browser_versions",
                )
            },
            ensure_ascii=False,
        )
    )
    if args.require_complete:
        assert complete and len(browsers) == 1, (
            "Formal matrix incomplete or browser versions differ"
        )


if __name__ == "__main__":
    main()
