"""Independently audit frozen route measurements without importing collector code."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import statistics
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ORIGIN = "http://127.0.0.1:9000"
SCENARIOS = (
    "cold-runs",
    "warm-runs",
    "first-form",
    "first-compare",
    "first-dataset",
    "first-forecast",
)
REVIEW = Path(__file__).resolve().parent
TASK = REVIEW.parents[1]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_entries(stage: dict) -> list[dict]:
    return [*stage["navigation"], *stage["resources"]]


def category(url: str) -> str:
    path = urlsplit(url).path
    if path.startswith("/assets/"):
        return "asset"
    if path.startswith("/api/"):
        return "api"
    return "other"


def aggregate(entries: list[dict]) -> dict:
    unique: dict[str, dict] = {}
    for entry in entries:
        old = unique.get(entry["name"])
        if old is None or entry["encodedBodySize"] > old["encodedBodySize"]:
            unique[entry["name"]] = entry
    result = {}
    for group in ("all", "asset", "api", "other"):
        members = [x for x in entries if group == "all" or category(x["name"]) == group]
        union = [x for x in unique.values() if group == "all" or category(x["name"]) == group]
        result[group] = {
            "request_entries": len(members),
            "unique_urls": len(union),
            "transfer_bytes": sum(x["transferSize"] for x in members),
            "encoded_body_union": sum(x["encodedBodySize"] for x in union),
            "decoded_body_union": sum(x["decodedBodySize"] for x in union),
            "urls": sorted(x["name"] for x in union),
        }
    return result


def stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "values": values,
    }


def numeric_leaves(value: dict, prefix: str = "") -> dict[str, float]:
    result = {}
    for name, child in value.items():
        key = f"{prefix}.{name}" if prefix else name
        if isinstance(child, dict):
            result.update(numeric_leaves(child, key))
        elif isinstance(child, (int, float)) and not isinstance(child, bool):
            result[key] = child
    return result


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0
        self.paint: list[dict] = []
        self.http: Counter = Counter()

    def check(self, condition: bool, description: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(description)

    def equal(self, actual: object, expected: object, description: str) -> None:
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            self.check(math.isclose(actual, expected, abs_tol=0.00001), description)
        else:
            self.check(actual == expected, description)

    def snapshot(self, stage: dict, label: str) -> None:
        self.equal(stage["duration"], stage["end"] - stage["start"], label + " duration")
        paint = stage["paintCollection"]
        self.equal(paint["readyEndpoint"], stage["end"], label + " ready endpoint")
        self.equal(paint["timeoutMs"], 1000, label + " paint limit")
        self.equal(paint["scope"], "document", label + " paint scope")
        self.equal(
            paint["waitMs"],
            paint["collectedAt"] - paint["startedAt"],
            label + " separate paint wait",
        )
        self.check(paint["startedAt"] >= stage["end"], label + " paint after ready")
        fcp = [x["startTime"] for x in stage["paint"] if x["name"] == "first-contentful-paint"]
        initial = [
            x["startTime"] for x in stage["paintAtReady"] if x["name"] == "first-contentful-paint"
        ]
        self.equal(paint["status"], "observed", label + " native FCP observed")
        self.equal(len(fcp), 1, label + " one native FCP")
        self.check(all(x in fcp for x in initial), label + " retain original FCP")
        self.paint.append(
            {
                "label": label,
                "time_origin": stage["timeOrigin"],
                "status": paint["status"],
                "fcp": fcp,
                "missing_at_ready": not initial,
                "wait_ms": paint["waitMs"],
                "fcp_after_ready": bool(fcp and fcp[0] > stage["end"]),
            }
        )
        for resource in stage_entries(stage):
            self.check(resource["name"].startswith(ORIGIN + "/"), label + " local resource")
            self.check(resource["responseEnd"] <= stage["end"], label + " frozen resource")

    def accounting(self, recorded: dict, recomputed: dict, label: str) -> None:
        all_resources = recomputed["all"]
        keys = {
            "uniqueUrlCount": "unique_urls",
            "requestEntryCount": "request_entries",
            "transferBytesSum": "transfer_bytes",
            "encodedBodyBytesUrlUnion": "encoded_body_union",
            "decodedBodyBytesUrlUnion": "decoded_body_union",
        }
        for old, new in keys.items():
            self.equal(recorded[old], all_resources[new], f"{label} {old}")
        self.equal(
            sorted(x["url"] for x in recorded["urls"]),
            all_resources["urls"],
            label + " full URL union",
        )

    def observation(self, item: dict, file: Path, experiment: dict) -> dict:
        label = file.name
        identity = experiment["measurement_identity"]
        variant = item["variant"]
        self.equal(item["instrumentation"], identity, label + " tool identity")
        self.equal(item["product"], identity["variants"][variant], label + " product identity")
        self.equal(item["viewport"], {"width": 1280, "height": 900}, label + " viewport")
        self.equal(item["deviceScaleFactor"], 1, label + " DPR")
        self.equal(item["pageErrors"], [], label + " browser errors")
        source, target = item["stages"][0], item["stages"][-1]
        for index, stage in enumerate(item["stages"]):
            self.snapshot(stage, f"{label}:stages:{index}")
        source_entries, target_entries = stage_entries(source), stage_entries(target)
        self.check(
            all(
                x["transferSize"] > 0 and x["responseStatus"] == 200
                for x in source_entries
                if category(x["name"]) == "asset"
            ),
            label + " cold source assets transferred",
        )
        windows = {"entry": aggregate(source_entries), "cumulative": aggregate(target_entries)}
        if item["scenario"] == "warm-runs":
            windows["warm"] = aggregate(target_entries)
            windows["cumulative"] = aggregate(source_entries + target_entries)
            self.accounting(
                item["accounting"]["coldPrime"], windows["entry"], label + " cold prime"
            )
            self.accounting(item["accounting"]["warm"], windows["warm"], label + " warm")
            self.equal(
                windows["warm"]["asset"]["transfer_bytes"], 0, label + " warm asset transfer"
            )
        elif item["scenario"] == "journey":
            self.accounting(
                item["accounting"]["completeJourney"], windows["cumulative"], label + " journey"
            )
            self.equal(len(item["stages"]), 10, label + " journey stages")
            expected_assets = sorted(
                ORIGIN + "/" + x
                for x in experiment["variants"][variant]["build"]["files"]
                if x.startswith("assets/")
            )
            self.equal(
                windows["cumulative"]["asset"]["urls"],
                expected_assets,
                label + " complete build asset union",
            )
        else:
            self.accounting(item["accounting"]["entry"], windows["entry"], label + " entry")
            self.accounting(
                item["accounting"]["cumulative"], windows["cumulative"], label + " cumulative"
            )
            if len(item["stages"]) > 1:
                source_urls = {x["name"] for x in source_entries}
                navigation = [
                    x
                    for x in target_entries
                    if x["startTime"] >= target["start"] and x["responseEnd"] <= target["end"]
                ]
                increment = [x for x in navigation if x["name"] not in source_urls]
                windows["navigation"] = aggregate(navigation)
                windows["increment"] = aggregate(increment)
                self.accounting(
                    item["accounting"]["navigationWindow"],
                    windows["navigation"],
                    label + " navigation",
                )
                self.accounting(
                    item["accounting"]["navigationIncrement"],
                    windows["increment"],
                    label + " increment",
                )
        result = {
            "file": str(file),
            "sha256": sha(file),
            "variant": variant,
            "scenario": item["scenario"],
            "sample": item["sample"],
            "attempt": item["attempt"],
            "ready_ms": target["end"] - target["start"],
            "windows": windows,
        }
        self.equal(item["primaryReadyMilliseconds"], result["ready_ms"], label + " primary ready")
        if item.get("preview"):
            self.snapshot(item["preview"], label + ":preview")
            result["preview_ready_ms"] = item["preview"]["duration"]
            windows["with_preview"] = aggregate(stage_entries(item["preview"]))
            if item.get("accountingWithPreview"):
                self.accounting(
                    item["accountingWithPreview"], windows["with_preview"], label + " preview"
                )
        if item["scenario"] in ("cold-runs", "warm-runs"):
            result["fcp_ms"] = next(
                x["startTime"] for x in target["paint"] if x["name"] == "first-contentful-paint"
            )
        if variant == "B1" and source["route"] == "/runs":
            pages = [
                Path(urlsplit(url).path).name
                for url in windows["entry"]["asset"]["urls"]
                if "Page-" in url
            ]
            self.check(
                len(pages) == 1 and pages[0].startswith("RunsPage-"),
                label + " no other page prefetched",
            )
        build = experiment["variants"][variant]["build"]["files"]
        for resource in target_entries:
            if category(resource["name"]) != "asset":
                continue
            name = urlsplit(resource["name"]).path.lstrip("/")
            self.check(name in build, label + " asset in frozen dist")
            if name in build:
                self.equal(
                    resource["encodedBodySize"],
                    build[name]["bytes"],
                    label + " encoded bytes " + name,
                )
                self.equal(
                    resource["decodedBodySize"],
                    build[name]["bytes"],
                    label + " decoded bytes " + name,
                )
        for request in item["network"]:
            self.check(
                request.get("method") in (None, "GET", "HEAD", "OPTIONS"),
                label + " no mutating HTTP",
            )
            if category(request.get("url", "")) != "asset":
                continue
            self.http["asset_responses"] += 1
            headers = {k.lower(): v for k, v in request.get("responseHeaders", {}).items()}
            self.http["with_content_encoding"] += bool(headers.get("content-encoding"))
            self.http["with_cache_control"] += bool(headers.get("cache-control"))
            self.http[request.get("cacheClassification", "unspecified")] += 1
            self.check(not headers.get("content-encoding"), label + " asset uncompressed")
            self.check(request.get("status") in (200, 304), label + " asset response status")
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--journey", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().parent != REVIEW or args.output.exists():
        raise ValueError("Use a new output file in evidence/review")
    experiment = read(args.experiment)
    identity = experiment["measurement_identity"]
    audit = Audit()
    for name, expected in identity["scripts"].items():
        audit.equal(sha(TASK / "tools" / name), expected, "frozen tool " + name)
    builds = {}
    for variant, value in experiment["variants"].items():
        root = Path(value["root"])
        for name, expected in value["source"]["files"].items():
            audit.equal(sha(root / name), expected["sha256"], variant + " source " + name)
        files = {}
        dist = root / "web/dist"
        audit.equal(
            sorted(p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()),
            sorted(value["build"]["files"]),
            variant + " dist file set",
        )
        for name, expected in value["build"]["files"].items():
            body = (dist / name).read_bytes()
            audit.equal(
                hashlib.sha256(body).hexdigest(), expected["sha256"], variant + " dist " + name
            )
            audit.equal(len(body), expected["bytes"], variant + " dist bytes " + name)
            files[name] = {
                "bytes": len(body),
                "gzip_estimate": len(gzip.compress(body, compresslevel=9, mtime=0)),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
            audit.equal(
                files[name]["gzip_estimate"],
                expected["gzip_bytes"],
                variant + " independent gzip " + name,
            )
        builds[variant] = {
            "files": files,
            "file_count": len(files),
            "bytes": sum(x["bytes"] for x in files.values()),
            "gzip_estimate": sum(x["gzip_estimate"] for x in files.values()),
        }
        audit.equal(
            builds[variant]["bytes"],
            value["build"]["totals"]["bytes"],
            variant + " total raw bytes",
        )
        audit.equal(
            builds[variant]["gzip_estimate"],
            value["build"]["totals"]["gzip_bytes"],
            variant + " total gzip bytes",
        )
    observations, invalid = [], []
    orders = {}
    for directory, expected_count in ((args.raw, 60), (args.journey, 2)):
        audit.equal(
            read(directory.with_name(directory.name + "-instrumentation.json")),
            identity,
            str(directory) + " sidecar",
        )
        records = []
        for file in sorted(directory.glob("*.json")):
            item = read(file)
            if "scenario" not in item or "variant" not in item:
                continue
            if not item["valid"]:
                invalid.append({"file": str(file), "sha256": sha(file), "error": item.get("error")})
                continue
            records.append((file, item))
        audit.equal(len(records), expected_count, str(directory) + " valid count")
        chronological = sorted(records, key=lambda pair: pair[1]["startedAt"])
        run_order = []
        for _, item in chronological:
            key = (item["sample"], item["variant"])
            if not run_order or key != run_order[-1]:
                run_order.append(key)
        orders[str(directory)] = run_order
        expected_order = [
            (sample, variant)
            for sample in range(1, 6 if expected_count == 60 else 2)
            for variant in ("B0", "B1")
        ]
        audit.equal(run_order, expected_order, str(directory) + " observed alternating order")
        for file, item in records:
            audit.equal(
                item["experiment_manifest_sha256"],
                sha(args.experiment),
                file.name + " experiment identity",
            )
            observations.append(audit.observation(item, file, experiment))
    groups = {}
    by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in observations:
        by_group[(item["variant"], item["scenario"])].append(item)
    for variant in ("B0", "B1"):
        for scenario in (*SCENARIOS, "journey"):
            group = sorted(by_group[(variant, scenario)], key=lambda x: x["sample"])
            expected = 1 if scenario == "journey" else 5
            audit.equal(
                [x["sample"] for x in group],
                list(range(1, expected + 1)),
                f"{variant}/{scenario} samples",
            )
            if not group:
                continue
            metrics: dict[str, list[float]] = defaultdict(list)
            for item in group:
                for key, value in numeric_leaves(item).items():
                    if key not in ("sample", "attempt"):
                        metrics[key].append(value)
            groups[f"{variant}/{scenario}"] = {k: stats(v) for k, v in metrics.items()}
    documents = {(row["label"].split(":")[0], row["time_origin"]) for row in audit.paint}
    result = {
        "passed": not audit.failures,
        "checks": audit.checks,
        "failures": audit.failures,
        "invalid_attempts": invalid,
        "script_sha256": sha(Path(__file__)),
        "experiment_sha256": sha(args.experiment),
        "identity": identity,
        "gzip_runtime": {
            "python": platform.python_version(),
            "zlib": zlib.ZLIB_RUNTIME_VERSION,
            "method": "Per file gzip.compress(compresslevel=9, mtime=0)",
        },
        "builds": builds,
        "groups": groups,
        "observations": observations,
        "observed_order": orders,
        "http": dict(audit.http),
        "paint": {
            "snapshot_count": len(audit.paint),
            "document_count": len(documents),
            "missing_at_ready": sum(x["missing_at_ready"] for x in audit.paint),
            "fcp_after_ready": sum(x["fcp_after_ready"] for x in audit.paint),
            "wait_ms": stats([x["wait_ms"] for x in audit.paint]),
            "snapshots": audit.paint,
        },
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": audit.checks,
                "failures": audit.failures,
                "observations": len(observations),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
