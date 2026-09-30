"""Run alternating variants after the main session releases port 9000."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def occupied() -> bool:
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", 9000)) == 0


def fingerprint(root: Path) -> dict:
    return {
        path.relative_to(root).as_posix(): {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        for area in ("configs", "cache", "runs", "source")
        for path in sorted((root / area).rglob("*"))
        if path.is_file()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--playwright-root", type=Path, required=True)
    parser.add_argument("--browser-executable", type=Path, required=True)
    parser.add_argument("--sample-start", type=int, default=1)
    parser.add_argument("--sample-end", type=int, default=5)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--variants", default="B0,B1,B2")
    parser.add_argument(
        "--scenarios",
        default="cold-runs,warm-runs,first-form,first-compare,first-dataset,first-forecast",
    )
    args = parser.parse_args()
    root = args.experiment_root.resolve(strict=True)
    fixture = root / "fixtures"
    scripts = Path(__file__).resolve().parent
    args.output.mkdir(parents=True, exist_ok=True)
    if occupied():
        raise SystemExit("Port 9000 is occupied; ask the owning session to close its service")
    before = fingerprint(fixture)
    expected = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))["files"]
    assert before == expected, "Fixtures changed before matrix"
    all_variants = ["B0", "B1", "B2"]
    wanted = args.variants.split(",")
    assert wanted and set(wanted) <= set(all_variants)
    order = []
    for sample in range(args.sample_start, args.sample_end + 1):
        offset = (sample - 1) % 3
        for variant in all_variants[offset:] + all_variants[:offset]:
            if variant in wanted:
                order.append({"sample": sample, "variant": variant})
    suffix = f"s{args.sample_start}-{args.sample_end}-a{args.attempt}-" + "-".join(wanted)
    plan_file = args.output / f"order-{suffix}.json"
    if plan_file.exists():
        raise SystemExit("Existing matrix order preserved; use a new output directory or attempt")
    plan_file.write_text(
        json.dumps(
            {
                "order": order,
                "scenarios": args.scenarios.split(","),
                "created_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    lifecycle = []
    try:
        for item in order:
            if occupied():
                raise RuntimeError(
                    "Port 9000 became occupied; no unrelated process will be stopped"
                )
            variant, sample = item["variant"], item["sample"]
            log_path = args.output / f"service-{variant}-s{sample}-a{args.attempt}.log"
            with log_path.open("x", encoding="utf-8") as log:
                command = [
                    sys.executable,
                    str(scripts / "serve_variant.py"),
                    "--source-root",
                    str(root / "source"),
                    "--variant-root",
                    str(root / "variants" / variant),
                    "--fixture-root",
                    str(fixture),
                    "--model-cache",
                    str(root / "measurement" / "models"),
                ]
                process = subprocess.Popen(
                    command,
                    cwd=root,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                )
                status = dict(item, pid=process.pid, started_at=datetime.now(UTC).isoformat())
                lifecycle.append(status)
                try:
                    deadline = time.monotonic() + 30
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("Owned service exited before health check")
                        try:
                            with opener.open(
                                "http://127.0.0.1:9000/api/health", timeout=1
                            ) as response:
                                if response.status == 200:
                                    break
                        except OSError:
                            if time.monotonic() >= deadline:
                                raise RuntimeError("Owned service health check timed out") from None
                            time.sleep(0.1)
                    with opener.open("http://127.0.0.1:9000/", timeout=3) as response:
                        served = response.read()
                    expected_html = (
                        root / "variants" / variant / "web" / "dist" / "index.html"
                    ).read_bytes()
                    assert served == expected_html, "Served variant HTML differs from intended dist"
                    command = [
                        str(args.node),
                        str(scripts / "measure.mjs"),
                        "--playwright-root",
                        str(args.playwright_root),
                        "--browser-executable",
                        str(args.browser_executable),
                        "--fixture-root",
                        str(fixture),
                        "--output",
                        str(args.output),
                        "--variant",
                        variant,
                        "--sample",
                        str(sample),
                        "--attempt",
                        str(args.attempt),
                        "--scenarios",
                        args.scenarios,
                    ]
                    result = subprocess.run(command, cwd=root, check=False)
                    status["measurement_exit_code"] = result.returncode
                    if result.returncode:
                        raise RuntimeError(
                            f"Measurement failure retained for {variant}, sample {sample}"
                        )
                finally:
                    if process.poll() is None:
                        try:
                            process.send_signal(
                                signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT
                            )
                            process.wait(timeout=15)
                            status["stop_method"] = "Owned process group interrupt"
                        except (OSError, subprocess.TimeoutExpired):
                            process.terminate()
                            process.wait(timeout=10)
                            status["stop_method"] = (
                                "Owned process terminate after interrupt unavailable"
                            )
                    status["exit_code"] = process.returncode
                    status["finished_at"] = datetime.now(UTC).isoformat()
                    status["port_9000_free"] = not occupied()
                    assert status["port_9000_free"], (
                        "Port remains occupied; no unrelated process will be stopped"
                    )
                assert fingerprint(fixture) == before, "Synthetic fixture changed"
    finally:
        result = {
            "lifecycle": lifecycle,
            "fixture_files_unchanged": fingerprint(fixture) == before,
            "fixture_file_count": len(before),
            "port_9000_free": not occupied(),
        }
        (args.output / f"lifecycle-{suffix}.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "completed_runs": len(lifecycle),
                "fixture_files_unchanged": True,
                "port_9000_free": True,
            }
        )
    )


if __name__ == "__main__":
    main()
