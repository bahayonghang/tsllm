"""Verify the frozen report against independent results and raw CDP records."""

import hashlib
import json
import re
import statistics
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

TASK = Path(".trellis/tasks/09-30-frontend-route-lazy-loading")
REVIEW = TASK / "evidence/review"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []

    def check(name, condition, actual=None):
        checks.append({"name": name, "passed": bool(condition), "actual": actual})

    commands = read(TASK / "evidence/scope/final-commands-2.json")
    for name, expected in commands["document_sha256"].items():
        check("document:" + name, sha(TASK / name) == expected, sha(TASK / name))
    for command in commands["checks"]:
        check("command:" + command["label"], command["exit_code"] == 0)
    staged = next(c for c in commands["checks"] if c["label"] == "staged-paths")
    check("staged_empty", not staged["stdout"].strip())
    evidence = (
        "product-gates.json",
        "numeric-review.json",
        "visible-review.json",
        "scope-final.json",
    )
    for name in evidence:
        data = read(REVIEW / name)
        check("independent:" + name, data["passed"] and not data["failures"])
    numeric = read(REVIEW / "numeric-review.json")
    report = (TASK / "report.md").read_text(encoding="utf-8")
    sections = {part.splitlines()[0].strip(): part for part in report.split("\n## ")[1:]}

    def row(section, label):
        for line in sections[section].splitlines():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0] == label:
                return cells[1:]
        raise ValueError((section, label))

    def median(variant, scenario, key):
        return numeric["groups"][variant + "/" + scenario][key]["median"]

    def formatted(values):
        return [f"{int(value):,}" for value in values]

    scenarios = [
        ("冷 /runs", "cold-runs"),
        ("暖 /runs", "warm-runs"),
        ("首次表单", "first-form"),
        ("首次对比", "first-compare"),
        ("首次数据集详情", "first-dataset"),
        ("首次预测详情", "first-forecast"),
    ]
    for label, scenario in scenarios:
        expected = []
        for variant in ("B0", "B1"):
            stats = numeric["groups"][variant + "/" + scenario]["ready_ms"]
            expected.append(f"{stats['median']:.1f}（{stats['min']:.1f}–{stats['max']:.1f}）")
        delta = median("B1", scenario, "ready_ms") - median("B0", scenario, "ready_ms")
        expected.append(f"{delta:+.1f}")
        check("readiness:" + scenario, row("六场景耗时", label) == expected, expected)
    for label, scenario in scenarios[:2]:
        expected = []
        for variant in ("B0", "B1"):
            stats = numeric["groups"][variant + "/" + scenario]["fcp_ms"]
            expected.append(f"{stats['median']:.1f}（{stats['min']:.1f}–{stats['max']:.1f}）")
        check("fcp:" + scenario, row("FCP边界", label) == expected, expected)
    cdp = {}
    for folder, scenario in (("raw-r1", "cold-runs"), ("journey-r1", "journey")):
        for variant in ("B0", "B1"):
            samples = []
            for path in sorted(
                (TASK / "evidence/measurement" / folder).glob(
                    variant + "-" + scenario + "-s*-a1.json"
                )
            ):
                data = read(path)
                all_bytes = sum(x.get("encodedDataLength", 0) for x in data["network"])
                asset_bytes = sum(
                    x.get("encodedDataLength", 0)
                    for x in data["network"]
                    if urlsplit(x["url"]).path.startswith("/assets/")
                )
                samples.append(
                    {
                        "file": path.relative_to(TASK).as_posix(),
                        "sha256": sha(path),
                        "all": all_bytes,
                        "asset": asset_bytes,
                    }
                )
            cdp[variant + "/" + scenario] = {
                "samples": samples,
                "all_median": statistics.median(x["all"] for x in samples),
                "asset_median": statistics.median(x["asset"] for x in samples),
            }
    cold_fields = {
        "资产请求及唯一URL数": "windows.entry.asset.unique_urls",
        "资产正文 B": "windows.entry.asset.encoded_body_union",
        "资产transferSize B": "windows.entry.asset.transfer_bytes",
        "全部transferSize B": "windows.entry.all.transfer_bytes",
    }
    for label, key in cold_fields.items():
        expected = formatted([median(v, "cold-runs", key) for v in ("B0", "B1")])
        check("cold:" + label, row("冷入口资源", label) == expected, expected)
    for label, field in (
        ("资产CDP encodedDataLength B", "asset_median"),
        ("全部CDP encodedDataLength B", "all_median"),
    ):
        expected = formatted([cdp[v + "/cold-runs"][field] for v in ("B0", "B1")])
        check("cold_cdp:" + label, row("冷入口资源", label) == expected, expected)
    gzip_values = []
    for variant in ("B0", "B1"):
        observation = next(
            o
            for o in numeric["observations"]
            if o["variant"] == variant and o["scenario"] == "cold-runs"
        )
        gzip_values.append(
            sum(
                numeric["builds"][variant]["files"][urlsplit(u).path.lstrip("/")]["gzip_estimate"]
                for u in observation["windows"]["entry"]["asset"]["urls"]
            )
        )
    expected = formatted(gzip_values)
    check("cold_gzip", row("冷入口资源", "入口资产离线gzip B") == expected, expected)
    for label, scenario in scenarios[2:]:
        expected = formatted(
            [
                median("B1", scenario, "windows.increment.asset." + field)
                for field in ("request_entries", "encoded_body_union", "transfer_bytes")
            ]
        )
        expected.append(
            " / ".join(
                formatted(
                    [
                        median(v, scenario, "windows.cumulative.all.transfer_bytes")
                        for v in ("B0", "B1")
                    ]
                )
            )
        )
        check("first_use:" + scenario, row("首次使用成本", label) == expected, expected)
    journey_fields = {
        "请求条目数": "windows.cumulative.all.request_entries",
        "完整URL并集数": "windows.cumulative.all.unique_urls",
        "全部transferSize B": "windows.cumulative.all.transfer_bytes",
        "资产transferSize B": "windows.cumulative.asset.transfer_bytes",
        "API transferSize B": "windows.cumulative.api.transfer_bytes",
    }
    for label, key in journey_fields.items():
        expected = formatted([median(v, "journey", key) for v in ("B0", "B1")])
        check("journey:" + label, row("完整访问成本", label) == expected, expected)
    expected = formatted([cdp[v + "/journey"]["all_median"] for v in ("B0", "B1")])
    check("journey_cdp", row("完整访问成本", "全部CDP encodedDataLength B") == expected, expected)
    for label, key in (
        ("全部构建文件正文 B", "bytes"),
        ("全部构建文件离线gzip B", "gzip_estimate"),
    ):
        expected = formatted([numeric["builds"][v][key] for v in ("B0", "B1")])
        check("build:" + label, row("完整访问成本", label) == expected, expected)
    prd = (TASK / "prd.md").read_text(encoding="utf-8")
    implementation = (TASK / "implement.md").read_text(encoding="utf-8")
    verification = (TASK / "verification.md").read_text(encoding="utf-8")
    check("prd_ten_accepted", len(re.findall(r"^- \[x\] AC\d+ ", prd, re.M)) == 10)
    check("implementation_ten_done", len(re.findall(r"^\d+\. \[x\]", implementation, re.M)) == 10)
    check("verification_ten_pass", len(re.findall(r"^\| \d+ \| 通过", verification, re.M)) == 10)
    check(
        "reload_limit_disclosed",
        all(
            s in verification
            for s in ("timeOrigin/navigation.type", "expectNavigation(waitUntil=load)", "未取得")
        ),
    )
    check("warm_cause_disclosed", "精确原因未查明" in report and "精确原因未查明" in verification)
    cleanup = read(TASK / "evidence/measurement/cleanup-r1.json")
    lifecycles = []
    for folder in ("raw-r1", "journey-r1"):
        path = next((TASK / "evidence/measurement" / folder).glob("lifecycle*.json"))
        lifecycle = read(path)
        lifecycles.extend(lifecycle["lifecycle"])
        check(
            "fixture:" + folder,
            lifecycle["fixture_files_unchanged"] and lifecycle["port_9000_free"],
        )
    check("lifecycle_summary_exact", lifecycles == cleanup["lifecycles"])
    check(
        "twelve_owned_services", len(lifecycles) == 12 and len({x["pid"] for x in lifecycles}) == 12
    )
    check(
        "service_stop_codes",
        all(
            x["measurement_exit_code"] == 0 and x["exit_code"] == 3 and x["port_9000_free"]
            for x in lifecycles
        ),
    )
    scope = read(TASK / "evidence/scope/final.json")
    for key in ("product_files", "spec_files"):
        for name, expected in scope[key].items():
            check("current_file:" + name, sha(Path(name)) == expected["sha256"])
    spec = Path(".trellis/spec/frontend/directory-structure.md").read_text(encoding="utf-8")
    check("recovery_spec", "event.preventDefault()" in spec and "location.reload()" in spec)
    failed = [item for item in checks if not item["passed"]]
    result = {
        "passed": not failed,
        "recorded_at": datetime.now(UTC).isoformat(),
        "checks": len(checks),
        "failures": failed,
        "items": checks,
        "script_sha256": sha(Path(__file__)),
        "document_sha256": commands["document_sha256"],
        "final_commands_sha256": sha(TASK / "evidence/scope/final-commands-2.json"),
        "cdp": cdp,
        "evidence_sha256": {name: sha(REVIEW / name) for name in evidence},
    }
    with (REVIEW / "final-documents.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({"passed": not failed, "checks": len(checks), "failures": failed}))
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
