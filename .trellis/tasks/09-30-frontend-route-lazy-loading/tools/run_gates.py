"""Run exact package scripts with installed binaries and preserve every attempt."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from acceptance_common import TASK, record, verify, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--gates", nargs="+", default=["check", "test", "build"])
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    root = Path(snapshot["root"])
    verify(snapshot["files"], root)
    scripts = json.loads((root / "web/package.json").read_text(encoding="utf-8"))["scripts"]
    expected = {
        "check": "biome check . && tsc --noEmit",
        "test": "vitest run",
        "build": "tsc --noEmit && vite build",
    }
    if any(scripts[key] != command for key, command in expected.items()):
        raise RuntimeError("Package scripts changed; review the gate contract")
    evidence = TASK / "evidence/gates"
    evidence.mkdir(parents=True, exist_ok=True)
    results = []
    for gate in args.gates:
        if gate not in expected:
            raise ValueError(gate)
        attempt = 1
        while (evidence / f"{root.name}-{gate}-{attempt}.json").exists() or (
            evidence / f"{root.name}-{gate}-{attempt}.txt"
        ).exists():
            attempt += 1
        stem = f"{root.name}-{gate}-{attempt}"
        started, start = datetime.now(UTC).isoformat(), time.perf_counter()
        components, output = [], []
        for part in scripts[gate].split(" && "):
            words = shlex.split(part)
            executable = root / "web/node_modules/.bin" / f"{words[0]}.CMD"
            if not executable.is_file():
                raise FileNotFoundError(executable)
            command = [str(executable), *words[1:]]
            result = subprocess.run(
                command,
                cwd=root / "web",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            output.append(result.stdout + "\n" + result.stderr)
            components.append(
                {"argv": command, "exit_code": result.returncode, "launcher": record(executable)}
            )
            if result.returncode:
                break
        text = "\n".join(output)
        with (evidence / f"{stem}.txt").open("x", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n")
        item = {
            "variant": snapshot["variant"],
            "root": str(root),
            "source_version": snapshot["source_version"],
            "gate": gate,
            "attempt": attempt,
            "command": scripts[gate],
            "components": components,
            "started_utc": started,
            "duration_seconds": time.perf_counter() - start,
            "exit_code": result.returncode,
            "log": f"{stem}.txt",
            "runner": record(Path(__file__)),
            "invocation": (
                "Installed .bin launchers; exact package.json script; "
                "no pnpm preparation or installation"
            ),
        }
        write_json(evidence / f"{stem}.json", item)
        results.append(item)
        print(
            json.dumps(
                {
                    key: item[key]
                    for key in ("variant", "gate", "attempt", "exit_code", "duration_seconds")
                }
            ),
            flush=True,
        )
    verify(snapshot["files"], root)
    raise SystemExit(0 if all(item["exit_code"] == 0 for item in results) else 1)


if __name__ == "__main__":
    main()
