"""Verify final variant files and emitted assets without rebuilding or modifying them."""

import argparse
import gzip
import hashlib
import json
import platform
import zlib
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = args.experiment_root / "source"
    variant_evidence = args.evidence / "variants"
    baseline_names = {
        p.relative_to(baseline).as_posix() for p in (baseline / "web").rglob("*") if p.is_file()
    }
    results = []
    for variant in ("B0", "B1", "B2"):
        root = args.experiment_root / "variants" / variant
        inventory = json.loads(
            (variant_evidence / f"{variant}-inventory.json").read_text(encoding="utf-8")
        )
        expected = {row["file"]: row for row in inventory["source_changes"]}
        assert digest(variant_evidence / f"{variant}.patch") == inventory["patch_sha256"]
        names = baseline_names | {
            p.relative_to(root).as_posix()
            for folder in ("src", "tests")
            for p in (root / "web" / folder).rglob("*")
            if p.is_file()
        }
        changes = {}
        for name in sorted(names - {"web/vite.config.ts"}):
            before, after = digest(baseline / name), digest(root / name)
            if before != after:
                changes[name] = {"file": name, "before_sha256": before, "after_sha256": after}
        assert changes == expected, (variant, "source changes differ")
        original_tests = [name for name in baseline_names if name.startswith("web/tests/")]
        assert all(digest(root / name) == digest(baseline / name) for name in original_tests)
        for name in ("package.json", "pnpm-lock.yaml", "openapi.json", "src/api/schema.d.ts"):
            assert digest(root / "web" / name) == digest(baseline / "web" / name), (variant, name)
        config = (baseline / "web/vite.config.ts").read_text(encoding="utf-8")
        config = config.replace(
            'import { defineConfig } from "vitest/config";',
            'import { defineConfig } from "vitest/config";\n'
            'import { assessmentGraph } from "./assessmentGraph";',
        )
        config = config.replace("plugins: [react()]", "plugins: [react(), assessmentGraph()]")
        assert (root / "web/vite.config.ts").read_bytes() == config.encode("utf-8")
        assert digest(root / "web/assessmentGraph.ts") == digest(
            variant_evidence / "assessmentGraph.ts"
        )
        assert digest(root / "assessment/graph.json") == digest(
            variant_evidence / f"{variant}-graph.json"
        )
        actual_assets = {
            p.relative_to(root / "web/dist").as_posix()
            for p in (root / "web/dist").rglob("*")
            if p.is_file()
        }
        assert actual_assets == {item["file"] for item in inventory["assets"]}
        assert inventory["gzip_estimate"]["python"] == platform.python_version()
        assert inventory["gzip_estimate"]["zlib"] == zlib.ZLIB_RUNTIME_VERSION
        for asset in inventory["assets"]:
            data = (root / "web/dist" / asset["file"]).read_bytes()
            assert len(data) == asset["bytes"]
            assert hashlib.sha256(data).hexdigest() == asset["sha256"]
            assert len(gzip.compress(data, compresslevel=9, mtime=0)) == asset["gzip_bytes"]
        assert sum(asset["bytes"] for asset in inventory["assets"]) == inventory["total_bytes"]
        assert (
            sum(asset["gzip_bytes"] for asset in inventory["assets"])
            == inventory["total_gzip_bytes"]
        )
        graph = json.loads((variant_evidence / f"{variant}-graph.json").read_text(encoding="utf-8"))
        for chunk in graph["chunks"]:
            assert chunk["file"] in actual_assets
            assert all(name in actual_assets for name in chunk["imports"] + chunk["dynamicImports"])
        gates = {}
        scripts = json.loads((root / "web/package.json").read_text(encoding="utf-8"))["scripts"]
        for gate in ("check", "test", "build"):
            records = [
                json.loads(p.read_text(encoding="utf-8"))
                for p in (args.evidence / "variant-gates").glob(f"{variant}-{gate}-*.json")
            ]
            last = max(records, key=lambda item: item["attempt"])
            assert last["exit_code"] == 0, (variant, gate)
            assert last["command"] == scripts[gate]
            log = args.evidence / "variant-gates" / last["log"]
            assert log.is_file()
            gates[gate] = {"attempt": last["attempt"], "exit_code": 0, "log_sha256": digest(log)}
        results.append(
            {
                "variant": variant,
                "source_changes": sorted(changes),
                "original_test_files_unchanged": len(original_tests),
                "assets_checked": len(actual_assets),
                "bytes": inventory["total_bytes"],
                "gzip_estimate_bytes": inventory["total_gzip_bytes"],
                "graph_reference_integrity": True,
                "latest_gates": gates,
            }
        )
    output = {
        "passed": True,
        "python": platform.python_version(),
        "zlib": zlib.ZLIB_RUNTIME_VERSION,
        "variants": results,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "passed": True,
                "variants": [
                    {k: v for k, v in row.items() if k not in {"source_changes", "latest_gates"}}
                    for row in results
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
