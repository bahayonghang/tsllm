"""Run unchanged frontend gate commands and retain every attempt."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--gates", nargs="+", default=["check", "test", "build"])
args = parser.parse_args()
args.evidence.mkdir(parents=True, exist_ok=True)
scripts = json.loads((args.root / "web/package.json").read_text(encoding="utf-8"))["scripts"]
all_pass = True
for gate in args.gates:
    attempts = list(args.evidence.glob(f"{args.root.name}-{gate}-*.json"))
    stem = f"{args.root.name}-{gate}-{len(attempts) + 1}"
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    chunks = []
    for part in scripts[gate].split(" && "):
        words = shlex.split(part)
        executable = args.root / "web/node_modules/.bin" / f"{words[0]}.CMD"
        if not executable.is_file():
            raise FileNotFoundError(executable)
        result = subprocess.run([str(executable), *words[1:]], cwd=args.root / "web",
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        chunks.append(result.stdout + "\n" + result.stderr)
        if result.returncode:
            break
    duration = time.perf_counter() - clock
    output = "\n".join(chunks)
    for path, label in [(args.root.parent.parent, "<assessment-temp>"),
                        (Path(__file__).resolve().parents[5], "<repository>"),
                        (args.root.parent.parent.parent, "<temp>")]:
        for prefix in [str(path), path.as_posix(), str(path).replace(chr(92), chr(92) * 2)]:
            output = output.replace(prefix, label)
    output = "\n".join(line.rstrip() for line in output.splitlines()).rstrip() + "\n"
    (args.evidence / f"{stem}.txt").write_text(output, encoding="utf-8", newline="\n")
    record = {"variant": args.root.name, "gate": gate, "attempt": len(attempts) + 1,
              "command": scripts[gate], "working_directory": "<variant>/web",
              "launcher": "installed .bin commands; identical package.json script, pnpm 12 automatic install bypassed", "started_utc": started,
              "duration_seconds": duration, "exit_code": result.returncode,
              "log": f"{stem}.txt"}
    (args.evidence / f"{stem}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record), flush=True)
    all_pass = all_pass and result.returncode == 0
raise SystemExit(0 if all_pass else 1)
