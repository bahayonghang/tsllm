"""Build report tables from retained browser records without importing the summarizer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from urllib.parse import urlsplit

TASK = Path(__file__).resolve().parents[2]
VARIANTS = ("B0", "B1", "B2")
SCENARIOS = (
    "cold-runs",
    "warm-runs",
    "first-form",
    "first-compare",
    "first-dataset",
    "first-forecast",
)
ALIASES = {
    "request_entries": "requests",
    "unique_urls": "urls",
    "transfer_bytes_sum": "transfer",
    "encoded_body_url_union": "body",
    "decoded_body_url_union": "decoded_body",
    "asset_url_count": "asset_urls",
    "asset_encoded_body_union": "asset_body",
    "asset_decoded_body_union": "asset_decoded_body",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stats(values: list[float | None]) -> dict:
    present = [value for value in values if value is not None]
    return {
        "n": len(present),
        "observations": len(values),
        "median": median(present) if present else None,
        "min": min(present) if present else None,
        "max": max(present) if present else None,
        "values": values,
    }


def entries(stage: dict) -> list[dict]:
    return [*stage["navigation"], *stage["resources"]]


def category(url: str) -> str:
    path = urlsplit(url).path
    return (
        "asset" if path.startswith("/assets/") else "api" if path.startswith("/api/") else "other"
    )


def resources(events: list[dict]) -> tuple[dict, list[dict]]:
    unique: dict[str, dict] = {}
    for event in events:
        assert event["name"].startswith("http://127.0.0.1:9000/")
        old = unique.get(event["name"])
        if old is None or old["encodedBodySize"] < event["encodedBodySize"]:
            unique[event["name"]] = event
    result = {
        "requests": len(events),
        "urls": len(unique),
        "transfer": sum(e["transferSize"] for e in events),
        "body": sum(e["encodedBodySize"] for e in unique.values()),
        "decoded_body": sum(e["decodedBodySize"] for e in unique.values()),
    }
    for kind in ("asset", "api", "other"):
        chosen = [e for e in events if category(e["name"]) == kind]
        bodies = [e for url, e in unique.items() if category(url) == kind]
        result.update(
            {
                f"{kind}_requests": len(chosen),
                f"{kind}_urls": len(bodies),
                f"{kind}_body": sum(e["encodedBodySize"] for e in bodies),
                f"{kind}_decoded_body": sum(e["decodedBodySize"] for e in bodies),
                f"{kind}_transfer": sum(e["transferSize"] for e in chosen),
            }
        )
    urls = [
        {
            "url": url,
            "category": category(url),
            "body_bytes": event["encodedBodySize"],
        }
        for url, event in sorted(unique.items())
    ]
    return result, urls


def sample_values(sample: dict) -> dict:
    first, last = sample["stages"][0], sample["stages"][-1]
    source, target = entries(first), entries(last)
    windows = {"entry": source, "cumulative": target}
    if sample["scenario"] == "warm-runs":
        windows.update(warm=target, cumulative=source + target)
    elif len(sample["stages"]) > 1:
        navigation = [
            e for e in target if e["startTime"] >= last["start"] and e["responseEnd"] <= last["end"]
        ]
        old = {e["name"] for e in source}
        windows.update(
            navigation=navigation, increment=[e for e in navigation if e["name"] not in old]
        )
    result = {"ready_ms": last["end"] - last["start"]}
    assert math.isclose(result["ready_ms"], sample["primaryReadyMilliseconds"], abs_tol=1e-7)
    if sample.get("preview"):
        preview = sample["preview"]
        windows["with_preview"] = entries(preview)
        result["preview_ready_ms"] = preview["end"] - preview["start"]
    overlaps = [
        max(
            0,
            min(last["end"], item["startTime"] + item["duration"])
            - max(last["start"], item["startTime"]),
        )
        for item in last["longTasks"]
    ]
    result["completed_long_tasks_overlapping_window"] = sum(x > 0 for x in overlaps)
    result["completed_long_tasks_overlap_ms"] = sum(overlaps)
    result["observer_total_ms"] = (
        last["observerCostCumulative"]["totalMilliseconds"]
        - last["observerCostAtStart"]["totalMilliseconds"]
    )
    result["observer_document_max_predicate_ms"] = last["observerCostCumulative"]["maxMilliseconds"]
    if sample["scenario"] in ("cold-runs", "warm-runs"):
        paint = [x["startTime"] for x in last["paint"] if x["name"] == "first-contentful-paint"]
        assert len(paint) <= 1
        result["fcp_ms"] = paint[0] if paint else None
        result["dom_content_loaded_ms"] = last["navigation"][0]["domContentLoadedEventEnd"]
        result["load_event_ms"] = last["navigation"][0]["loadEventEnd"]
    measured = {key: resources(values) for key, values in windows.items()}
    return {
        "metrics": result,
        "windows": {key: value[0] for key, value in measured.items()},
        "url_sets": {key: value[1] for key, value in measured.items()},
    }


def delta(value: float | None, base: float | None) -> dict:
    if value is None or base is None:
        return {"absolute": None, "percent": None}
    return {"absolute": value - base, "percent": (value - base) / base * 100 if base else None}


def number(value: float) -> str:
    return f"{value:,.0f}"


def interval(value: dict) -> str:
    if not value["n"]:
        return f"未采得（0/{value['observations']}）"
    return f"{value['median']:.1f} [{value['min']:.1f}, {value['max']:.1f}]"


def change(value: float, base: float, digits: int = 0) -> str:
    result = delta(value, base)
    percent = "—" if result["percent"] is None else f"{result['percent']:+.2f}%"
    return f"{result['absolute']:+,.{digits}f} ({percent})"


def table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(row) + " |" for row in rows]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-root", type=Path, default=TASK / "evidence/measurement")
    parser.add_argument("--variant-root", type=Path, default=TASK / "evidence/variants")
    parser.add_argument("--report", type=Path, default=TASK / "report.md")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("recomputed.json"))
    parser.add_argument("--revision", default="original")
    args = parser.parse_args()
    inventories = {v: read(args.variant_root / f"{v}-inventory.json") for v in VARIANTS}
    grouped: dict[str, list[dict]] = defaultdict(list)
    hashes = {}
    checked = 0
    for folder in ("raw", "journey"):
        for path in sorted((args.measurement_root / folder).glob("B*-*.json")):
            sample = read(path)
            assert sample["valid"], path.name
            assert sample["viewport"] == {"width": 1280, "height": 900}
            row = sample_values(sample)
            row["file"] = path.name
            row["sample"] = sample["sample"]
            hashes[f"{folder}/{path.name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
            assets = {"/" + a["file"]: a["bytes"] for a in inventories[sample["variant"]]["assets"]}
            for urls in row["url_sets"].values():
                for url in urls:
                    if url["category"] == "asset":
                        assert assets[urlsplit(url["url"]).path] == url["body_bytes"]
            grouped[f"{sample['variant']}:{sample['scenario']}"].append(row)
    groups = {}
    for key, rows in grouped.items():
        _, scenario = key.split(":")
        assert len(rows) == (1 if scenario == "journey" else 5)
        assert len({r["sample"] for r in rows}) == len(rows)
        groups[key] = {
            "n": len(rows),
            "metrics": {
                name: stats([r["metrics"][name] for r in rows]) for name in rows[0]["metrics"]
            },
            "windows": {
                window: {
                    name: stats([r["windows"][window][name] for r in rows]) for name in metrics
                }
                for window, metrics in rows[0]["windows"].items()
            },
            "observations": rows,
        }
        summary_name = "journey-summary.json" if scenario == "journey" else "summary.json"
        summary = read(args.measurement_root / summary_name)["groups"][key]
        for metric, computed in groups[key]["metrics"].items():
            if metric not in summary:
                continue
            for stat in ("median", "min", "max"):
                assert math.isclose(computed[stat], summary[metric][stat], abs_tol=1e-7), (
                    key,
                    metric,
                )
                checked += 1
        for window, values in groups[key]["windows"].items():
            for original, name in ALIASES.items():
                for stat in ("median", "min", "max"):
                    assert math.isclose(
                        values[name][stat], summary["windows"][window][original][stat]
                    )
                    checked += 1
    assert len(groups) == 21 and len(hashes) == 93

    def metric(v: str, scene: str, name: str = "ready_ms") -> dict:
        return groups[f"{v}:{scene}"]["metrics"][name]

    def window(v: str, scene: str, name: str, key: str) -> float:
        return groups[f"{v}:{scene}"]["windows"][name][key]["median"]

    comparisons = {}
    for v, base in (("B1", "B0"), ("B2", "B0"), ("B2", "B1")):
        comparison = {}
        for scene in (*SCENARIOS, "journey"):
            current, reference = groups[f"{v}:{scene}"], groups[f"{base}:{scene}"]
            comparison[scene] = {
                "metrics": {
                    k: delta(x["median"], reference["metrics"][k]["median"])
                    for k, x in current["metrics"].items()
                },
                "windows": {
                    w: {
                        k: delta(x["median"], reference["windows"][w][k]["median"])
                        for k, x in m.items()
                    }
                    for w, m in current["windows"].items()
                },
            }
        comparisons[f"{v}_vs_{base}"] = comparison

    sections = [
        f"数据修订：`{args.revision}`。数值引用本修订的全部原始记录与对应方案资产。",
        "### 4.1 正式构建总量与离线压缩估算",
    ]
    rows = []
    for v in VARIANTS:
        inv = inventories[v]
        assert sum(a["bytes"] for a in inv["assets"]) == inv["total_bytes"]
        assert sum(a["gzip_bytes"] for a in inv["assets"]) == inv["total_gzip_bytes"]
        rows.append(
            [
                v,
                str(len(inv["assets"])),
                number(inv["total_bytes"]),
                number(inv["total_gzip_bytes"]),
                change(inv["total_bytes"], inventories["B0"]["total_bytes"]),
                change(inv["total_gzip_bytes"], inventories["B0"]["total_gzip_bytes"]),
            ]
        )
    sections.append(
        table(
            [
                "方案",
                "文件数（含 HTML）",
                "原始 B",
                "gzip 估算 B",
                "原始量相对 B0",
                "gzip 估算相对 B0",
            ],
            rows,
        )
    )
    sections.append(
        "两个拆分方案的文件总量均高于 B0。实际资产传输没有 gzip 压缩，不能使用本表压缩估算替代。"
    )

    sections.append("### 4.2 冷入口与缓存复用的实际资源")
    rows = []
    for scene, name in (("cold-runs", "entry"), ("warm-runs", "warm")):
        for v in VARIANTS:
            values = [
                window(v, scene, name, k)
                for k in (
                    "asset_urls",
                    "asset_body",
                    "asset_transfer",
                    "api_transfer",
                    "other_transfer",
                    "transfer",
                    "requests",
                )
            ]
            rows.append([v, scene, *[number(x) for x in values]])
    sections.append(
        table(
            [
                "方案",
                "场景",
                "资产 URL",
                "资产 body B",
                "资产 transfer B",
                "API transfer B",
                "HTML/其他 transfer B",
                "总 transfer B",
                "资源条目",
            ],
            rows,
        )
    )
    sections.append(
        "本表为 5 个观测的中位数，各组全部数值与范围保存在复算 JSON。"
        "热场景资产 body 表示缓存内容长度，资产 transfer 为 0。"
    )
    rows = []
    for v, base in (("B1", "B0"), ("B2", "B0"), ("B2", "B1")):
        rows.append(
            [
                f"{v}−{base}",
                *[
                    change(
                        window(v, "cold-runs", "entry", k), window(base, "cold-runs", "entry", k)
                    )
                    for k in ("asset_body", "transfer", "asset_urls")
                ],
            ]
        )
    sections.append(
        table(["冷入口对照", "资产 body B 变化", "总 transfer B 变化", "资产 URL 变化"], rows)
    )

    sections.append("### 4.3 18 组功能就绪时间")
    rows = []
    for scene in SCENARIOS:
        for v in VARIANTS:
            value = metric(v, scene)
            rows.append(
                [
                    scene,
                    v,
                    str(value["n"]),
                    interval(value),
                    change(value["median"], metric("B0", scene)["median"], 1),
                    change(value["median"], metric("B1", scene)["median"], 1) if v == "B2" else "—",
                ]
            )
    sections.append(
        table(
            [
                "场景",
                "方案",
                "n",
                "中位数 [最小, 最大] ms",
                "相对 B0：ms (%)",
                "B2 相对 B1：ms (%)",
            ],
            rows,
        )
    )
    sections.append(
        "所有样本和最大值均保留，没有删除预测详情的较慢观测。"
        "表格差值只描述样本，不等于稳定的总体性能变化。"
    )

    sections.append("### 4.4 首次导航新增与两页累计成本")
    rows = []
    for scene in SCENARIOS[2:]:
        for v in VARIANTS:
            rows.append(
                [
                    scene,
                    v,
                    *[
                        number(window(v, scene, w, k))
                        for w, k in (
                            ("entry", "asset_body"),
                            ("increment", "asset_urls"),
                            ("increment", "asset_body"),
                            ("navigation", "transfer"),
                            ("navigation", "requests"),
                            ("cumulative", "asset_body"),
                            ("cumulative", "transfer"),
                        )
                    ],
                ]
            )
    sections.append(
        table(
            [
                "场景",
                "方案",
                "源页资产 B",
                "新增资产 URL",
                "新增资产 B",
                "导航窗口 transfer B",
                "导航资源条目",
                "累计资产 B",
                "累计 transfer B",
            ],
            rows,
        )
    )
    sections.append(
        "字节与条目均为中位数。first-dataset 的源页为 /datasets，其他首次导航源页为 /runs。"
        "累计资源使用完整快照；导航窗口 transfer 含 API 与重复 URL。"
        "每个 URL 的归类和全部样本保存在 recomputed.json，不能把导航总量全归因于新资产。"
    )
    rows = []
    for scene in SCENARIOS[2:]:
        for v, base in (("B1", "B0"), ("B2", "B0"), ("B2", "B1")):
            rows.append(
                [
                    scene,
                    f"{v}−{base}",
                    *[
                        change(window(v, scene, w, k), window(base, scene, w, k))
                        for w, k in (
                            ("increment", "asset_body"),
                            ("navigation", "transfer"),
                            ("cumulative", "transfer"),
                        )
                    ],
                ]
            )
    sections.append(
        table(
            ["场景", "对照", "新增资产 B 变化", "导航 transfer B 变化", "累计 transfer B 变化"],
            rows,
        )
    )

    sections.append("### 4.5 表单预览")
    rows = []
    for v in VARIANTS:
        value = metric(v, "first-form", "preview_ready_ms")
        rows.append(
            [
                v,
                str(value["n"]),
                interval(value),
                change(
                    value["median"], metric("B0", "first-form", "preview_ready_ms")["median"], 1
                ),
                number(window(v, "first-form", "with_preview", "asset_body")),
                number(window(v, "first-form", "with_preview", "transfer")),
                number(
                    window(v, "first-form", "with_preview", "transfer")
                    - window(v, "first-form", "cumulative", "transfer")
                ),
            ]
        )
    sections.append(
        table(
            [
                "方案",
                "n",
                "预览就绪中位数 [最小, 最大] ms",
                "相对 B0：ms (%)",
                "预览后累计资产 B",
                "预览后累计 transfer B",
                "表单后至预览增量 B",
            ],
            rows,
        )
    )
    sections.append(
        "三个方案预览没有增加 JS 资产；模板读取计入表单就绪后至预览完成的区间。"
        "该资源区间包含模板选择，不等同于预览 click-to-ready 窗口。"
        "预览时间区间重叠；本指标不包含表单首次进入时间和模板操作时间。"
    )

    sections.append("### 4.6 完整访问补充旅程")
    rows = []
    for v in VARIANTS:
        rows.append(
            [
                v,
                "1",
                *[
                    number(window(v, "journey", "cumulative", k))
                    for k in (
                        "asset_urls",
                        "asset_body",
                        "asset_transfer",
                        "api_transfer",
                        "other_transfer",
                        "transfer",
                        "requests",
                        "urls",
                    )
                ],
            ]
        )
    sections.append(
        table(
            [
                "方案",
                "n",
                "资产 URL",
                "资产 body B",
                "资产 transfer B",
                "API transfer B",
                "HTML/其他 transfer B",
                "总 transfer B",
                "资源条目",
                "全部去重 URL",
            ],
            rows,
        )
    )
    rows = []
    for v, base in (("B1", "B0"), ("B2", "B0"), ("B2", "B1")):
        rows.append(
            [
                f"{v}−{base}",
                *[
                    change(
                        window(v, "journey", "cumulative", k),
                        window(base, "journey", "cumulative", k),
                    )
                    for k in ("asset_body", "transfer", "asset_urls", "requests")
                ],
            ]
        )
    sections.append(
        table(
            [
                "完整访问对照",
                "资产 body B 变化",
                "总 transfer B 变化",
                "资产 URL 变化",
                "资源条目变化",
            ],
            rows,
        )
    )
    sections.append(
        "全部 JS 资产均在完整旅程中出现；文件总量与资产 body 的差额为 index.html。"
        "完整 URL 集合包含共享块并只计一次 body，重复 API 请求保留 transfer。"
        "该旅程每方案仅 1 次，且原始 ready_ms 仅代表最后系统页导航，因此本表不报告完整旅程耗时。"
    )

    sections.append("### 4.7 文档绘制、长任务与观察器")
    rows = []
    for scene in SCENARIOS[:2]:
        for v in VARIANTS:
            rows.append(
                [
                    scene,
                    v,
                    *[
                        interval(metric(v, scene, name))
                        for name in ("fcp_ms", "dom_content_loaded_ms", "load_event_ms")
                    ],
                ]
            )
    sections.append(table(["文档场景", "方案", "FCP ms", "DOMContentLoaded ms", "load ms"], rows))
    sections.append(
        "各组观测数为 5；单元格为中位数 [最小, 最大]。未采得记录显示实际采集数，"
        "不填 0、不插补；缺少 FCP 的组无法参与完整三方案 FCP 对比。文档事件不替代功能就绪。"
    )
    rows = []
    for scene in SCENARIOS:
        for v in VARIANTS:
            rows.append(
                [
                    scene,
                    v,
                    *[
                        interval(metric(v, scene, name))
                        for name in (
                            "completed_long_tasks_overlapping_window",
                            "completed_long_tasks_overlap_ms",
                            "observer_total_ms",
                        )
                    ],
                ]
            )
    sections.append(
        table(["场景", "方案", "已完成交叠长任务数", "交叠 ms", "窗口观察器累计 ms"], rows)
    )
    sections.append(
        "各组 n=5；单元格为中位数 [最小, 最大]。0 仅表示观察窗口未记录已完成的交叠长任务。"
        "观察器成本已含在就绪时间内；没有从时间中扣除。长任务不能归因于某个依赖。"
        "文档累计最大 predicate 时间与窗口累计耗时分别保存在复算 JSON。"
    )
    sections.append("### 4.8 实际冷入口资产集合")
    sections.append(
        "以下为冷 /runs 就绪前实际出现的资产路径，均相对于同一个环回服务根地址。"
        "每组五个样本的资产 URL 集合逐一核对。首次导航新增、累计和完整旅程的所有 URL"
        "见复算 JSON 的 groups → observations → url_sets，按 asset/api/other 分类，保留查询参数。"
    )
    for variant in VARIANTS:
        observed = groups[f"{variant}:cold-runs"]["observations"]
        url_sets = [
            sorted(
                urlsplit(entry["url"]).path
                for entry in row["url_sets"]["entry"]
                if entry["category"] == "asset"
            )
            for row in observed
        ]
        assert all(urls == url_sets[0] for urls in url_sets)
        sections.append(
            f"{variant}，{len(url_sets[0])} 个资产 URL：\n\n```text\n"
            + "\n".join(url_sets[0])
            + "\n```"
        )

    artifact = {
        "revision": args.revision,
        "builds": inventories,
        "summary_sha256": {
            name: hashlib.sha256((args.measurement_root / name).read_bytes()).hexdigest()
            for name in ("summary.json", "journey-summary.json")
        },
        "baseline_commit": inventories["B0"]["baseline_commit"],
        "primary_observations": 90,
        "journey_observations": 3,
        "summary_numeric_assertions": checked,
        "raw_sha256": hashes,
        "groups": groups,
        "comparisons": comparisons,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    output = args.output
    output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = args.report
    text = report.read_text(encoding="utf-8")
    start, end = "<!-- generated-results:start -->", "<!-- generated-results:end -->"
    assert text.count(start) == text.count(end) == 1
    prefix, tail = text.split(start)
    _, suffix = tail.split(end)
    report.write_text(
        prefix + start + "\n" + "\n\n".join(sections) + "\n" + end + suffix, encoding="utf-8"
    )
    print(json.dumps({"observations": len(hashes), "groups": len(groups), "checks": checked}))


if __name__ == "__main__":
    main()
