"""Bind both formal builds and the observer scripts before visible acceptance."""

import argparse
import json
from pathlib import Path

from acceptance_common import TASK, record, verify, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--b1", default="B1-r1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    variants = {}
    for variant, stem in (("B0", "B0"), ("B1", args.b1)):
        source = json.loads(
            (TASK / f"evidence/snapshots/{stem}-source.json").read_text(encoding="utf-8")
        )
        build = json.loads(
            (TASK / f"evidence/snapshots/{stem}-build.json").read_text(encoding="utf-8")
        )
        assert source["source_version"] == build["source_version"]
        root = Path(source["root"])
        verify(source["files"], root)
        verify(build["files"], root / "web/dist")
        variants[variant] = {"root": str(root), "source": source, "build": build}
    fixture = TASK / "isolation/fixtures"
    fixture_manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
    verify(fixture_manifest["files"], fixture, mtimes=True)
    scripts = {
        name: record(TASK / "tools" / name)["sha256"]
        for name in (
            "browser_probe.mjs",
            "measure.mjs",
            "run_matrix.py",
            "serve_variant.py",
            "acceptance_common.py",
        )
    }
    identity = {
        "revision": "route-lazy-final-r1",
        "readiness_revision": "recovery-r1",
        "paint_revision": "paint-collection-r1",
        "scripts": scripts,
        "paintCollection": {
            "timeoutMs": 1000,
            "scope": "document",
            "beforeNextNavigationOrClose": True,
            "preservesReadySnapshot": True,
        },
        "fixture_manifest_sha256": record(fixture / "manifest.json")["sha256"],
        "variants": {
            key: {
                "source_version": value["source"]["source_version"],
                "dist_version": value["build"]["dist_version"],
            }
            for key, value in variants.items()
        },
    }
    output = {
        "schema_version": 1,
        "fixture_root": str(fixture),
        "source_root": str(TASK / "isolation/source"),
        "measurement_identity": identity,
        "variants": variants,
    }
    write_json(args.output, output)
    print(json.dumps({"experiment": str(args.output), "identity": identity}))


if __name__ == "__main__":
    main()
