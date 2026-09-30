"""Verify the assessment boundary without opening private data files."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = Path(__file__).resolve().parent
    baseline = json.loads((evidence / "baseline-tracked-sha256.json").read_text(encoding="utf-8"))
    protected = json.loads((evidence / "baseline-protected.json").read_text(encoding="utf-8"))

    def git(*parts: str) -> str:
        return subprocess.check_output(["git", *parts], cwd=repo).decode("utf-8").strip()

    changed = [name for name, expected in baseline.items() if digest(repo / name) != expected]
    tracked = set(git("ls-files").splitlines())
    private_tracked = [p for p in tracked if p.split("/", 1)[0] in {"data", "ref", "runs", "cache"}]
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    task_prefix = ".trellis/tasks/09-30-frontend-load-assessment/"
    outside_untracked = [p for p in untracked if not p.startswith(task_prefix)]
    launch_ok = digest(repo / ".claude/launch.json") == protected[".claude/launch.json"]
    backup_exists = (repo / "cache/datasets/ETTh1.acc-backup").exists()
    dist_changes = [
        name
        for name, expected in protected["original_dist"].items()
        if digest(repo / name) != expected
    ]
    current_dist = {
        p.relative_to(repo).as_posix() for p in (repo / "web/dist").rglob("*") if p.is_file()
    }
    dist_added = sorted(current_dist - set(protected["original_dist"]))
    dist_removed = sorted(set(protected["original_dist"]) - current_dist)
    result = {
        "baseline_commit": "e9ce26a7bd1a4ed67cd30d257354e7345c44dec1",
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "baseline_tracked_count": len(baseline),
        "changed_tracked_files": changed,
        "added_tracked_files": sorted(tracked - set(baseline)),
        "removed_tracked_files": sorted(set(baseline) - tracked),
        "staged_paths": git("diff", "--cached", "--name-only").splitlines(),
        "private_tracked_count": len(private_tracked),
        "outside_task_untracked": outside_untracked,
        "task_untracked_count": sum(p.startswith(task_prefix) for p in untracked),
        "launch_config_hash_unchanged": launch_ok,
        "backup_exists": backup_exists,
        "backup_content_read": False,
        "original_dist_changed": dist_changes,
        "original_dist_added": dist_added,
        "original_dist_removed": dist_removed,
    }
    result["passed"] = (
        result["head"] == result["baseline_commit"]
        and result["branch"] == "codex/frontend-load-assessment"
        and not changed
        and not result["added_tracked_files"]
        and not result["removed_tracked_files"]
        and not result["staged_paths"]
        and not private_tracked
        and not outside_untracked
        and launch_ok
        and backup_exists == protected["backup_exists"]
        and not dist_changes
        and not dist_added
        and not dist_removed
    )
    args.output.write_bytes(
        (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
