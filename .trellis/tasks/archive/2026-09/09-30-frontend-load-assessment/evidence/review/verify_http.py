"""Independently inspect actual asset headers and cold/warm cache outcomes."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sizes = {}
    for variant in ("B0", "B1", "B2"):
        inventory = json.loads(
            (args.variants / f"{variant}-inventory.json").read_text(encoding="utf-8")
        )
        sizes[variant] = {item["file"]: item["bytes"] for item in inventory["assets"]}
    encodings, policies, cold_statuses = Counter(), Counter(), Counter()
    warm_classes = defaultdict(Counter)
    cold_assets_checked = 0
    warm_asset_transfer_bytes = defaultdict(list)
    for file in sorted(args.raw.glob("B*-*.json")):
        item = json.loads(file.read_text(encoding="utf-8"))
        if not item.get("valid"):
            continue
        first_requests = {}
        for request in sorted(item["network"], key=lambda row: row.get("timestamp", 0)):
            if not urlsplit(request.get("url", "")).path.startswith("/assets/"):
                continue
            first_requests.setdefault(request["url"], request)
            headers = {
                key.lower(): value
                for source in (
                    request.get("responseHeaders", {}),
                    request.get("networkResponseHeaders", {}),
                )
                for key, value in source.items()
            }
            encodings[headers.get("content-encoding", "absent")] += 1
            policies[headers.get("cache-control", "absent")] += 1
            if (
                item["scenario"] == "warm-runs"
                and request.get("wallTime", 0) * 1000 >= item["warmStartWallTime"]
            ):
                warm_classes[item["variant"]][request["cacheClassification"]] += 1
        for event in item["stages"][0]["resources"]:
            asset = urlsplit(event["name"]).path.lstrip("/")
            if not asset.startswith("assets/"):
                continue
            request = first_requests[event["name"]]
            assert (
                not request.get("fromDiskCache")
                and not request.get("fromServiceWorker")
                and not request.get("requestServedFromCache")
            ), file.name
            assert request.get("networkStatusCode") != 304, file.name
            assert request["status"] == 200, file.name
            headers = {key.lower(): value for key, value in request["responseHeaders"].items()}
            assert int(headers["content-length"]) == sizes[item["variant"]][asset], file.name
            assert "content-encoding" not in headers, file.name
            assert event["transferSize"] > 0, file.name
            cold_assets_checked += 1
            cold_statuses[request["status"]] += 1
        if item["scenario"] == "warm-runs":
            warm_asset_transfer_bytes[item["variant"]].append(
                sum(
                    e["transferSize"]
                    for e in item["stages"][-1]["resources"]
                    if urlsplit(e["name"]).path.startswith("/assets/")
                )
            )
    result = {
        "passed": True,
        "cold_source_asset_entries_checked": cold_assets_checked,
        "cold_http_status_counts": dict(cold_statuses),
        "asset_content_encoding_counts": dict(encodings),
        "asset_cache_control_counts": dict(policies),
        "warm_asset_cache_classifications": {
            variant: dict(values) for variant, values in warm_classes.items()
        },
        "warm_asset_resource_timing_transfer_bytes": dict(warm_asset_transfer_bytes),
        "limits": [
            "Cache event without a disk flag does not prove a specific cache tier",
            "Resource Timing byte reports are not packet-capture measurements",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
