"""Check retained assessment artifacts without reading private directories."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    task = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("continuation-artifact-audit.json")
    )
    output = parser.parse_args().output.resolve()
    counts: Counter[str] = Counter()
    hashes: dict[str, str] = {}
    errors: list[str] = []
    whitespace: list[str] = []
    patch_context_lines = 0
    allowed = {".md", ".json", ".jsonl", ".py", ".mjs", ".ts", ".tsx", ".txt", ".patch", ".log"}
    for path in sorted(task.rglob("*")):
        if not path.is_file() or path == output:
            continue
        name = path.relative_to(task).as_posix()
        content = path.read_bytes()
        hashes[name] = hashlib.sha256(content).hexdigest()
        counts[path.suffix] += 1
        if path.suffix not in allowed:
            errors.append(f"Unexpected artifact type: {name}")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"Not UTF-8: {name}")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip(" \t") != line:
                if path.suffix == ".patch" and line == " ":
                    patch_context_lines += 1
                else:
                    whitespace.append(f"{name}:{number}")
        try:
            if path.suffix == ".json":
                json.loads(text)
            elif path.suffix == ".jsonl":
                for line in text.splitlines():
                    if line.strip():
                        json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"Invalid JSON: {name}: {error}")
    result = {
        "passed": not errors and not whitespace,
        "scope": "Current task directory only",
        "file_count": len(hashes),
        "suffix_counts": dict(sorted(counts.items())),
        "errors": errors,
        "trailing_whitespace": whitespace,
        "preserved_unified_diff_blank_context_lines": patch_context_lines,
        "files_sha256": hashes,
        "limits": [
            "No private directories opened",
            "File typing and JSON parsing do not by themselves prove data provenance",
            "Concurrent additions after this snapshot require a final rerun",
        ],
    }
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in result.items() if key != "files_sha256"}))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
