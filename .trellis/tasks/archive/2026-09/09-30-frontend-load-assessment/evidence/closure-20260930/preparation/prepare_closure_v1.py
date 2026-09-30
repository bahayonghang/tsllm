"""Audit frozen task files and preserve local closure inputs without Git writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

PREPARATION = Path(__file__).resolve().parent
TASK = PREPARATION.parents[2]
REPO = next(path for path in TASK.parents if (path / ".git").exists())
OLD_ROOT = ".trellis/tasks/09-30-frontend-load-assessment"
ARCHIVE_ROOT = ".trellis/tasks/archive/2026-09/09-30-frontend-load-assessment"
B1_ROOT = ".trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading"
ALLOWED = {".md", ".json", ".jsonl", ".py", ".mjs", ".ts", ".tsx", ".txt", ".patch", ".log"}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider_token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16})\b"
    ),
    "bearer_value": re.compile(
        r"(?i)authorization[\"']?\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._~+/=-]{16,}"
    ),
    "assigned_secret": re.compile(
        r"(?i)[\"']?(?:password|api[_-]?key|client[_-]?secret|access[_-]?token)"
        r"[\"']?\s*[:=]\s*[\"'][A-Za-z0-9._~+/=-]{16,}[\"']"
    ),
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def preserve(path: Path, raw: bytes) -> None:
    if path.exists():
        assert path.read_bytes() == raw, f"Refuse to replace different evidence: {path.name}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def purpose(relative: str) -> str:
    if not relative.startswith("evidence/"):
        return "规划、授权元数据、报告或上下文清单"
    area = relative.split("/")[1]
    return {
        "fixtures": "合成夹具生成器及文件元数据，未保存私有原始数据",
        "measurement": "浏览器计时、资源、服务生命周期、采集工具及首次失败",
        "report": "历史及 recovery-r1 报告、逐观测派生统计和复算工具",
        "review": "独立复算、检查工具、范围及首次检查失败记录",
        "scope": "历史 Git、文件哈希及受保护路径元数据",
        "variant-gates": "隔离方案正式门槛及全部失败和重试输出",
        "variants": "隔离源码补丁、构建清单、依赖图及恢复前后版本",
        "visible": "双视口可见验收、真实缺块恢复和清理记录",
    }[area]


def large_json_review(value: dict) -> dict:
    groups = value["groups"]
    leaves = 0
    url_hosts: Counter[str] = Counter()
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        else:
            leaves += 1
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                url_hosts[urlsplit(item).hostname or ""] += 1
    return {
        "top_level_keys": list(value),
        "revision": value["revision"],
        "primary_observations": value["primary_observations"],
        "journey_observations": value["journey_observations"],
        "group_count": len(groups),
        "group_counts": {key: group["n"] for key, group in groups.items()},
        "leaf_values_examined": leaves,
        "url_hosts": dict(sorted(url_hosts.items())),
        "purpose": "合成浏览器观测的统计和 URL 集合；保留历史与最终修订的完整复算",
    }


def verify_preserved() -> None:
    preflight = json.loads((PREPARATION.parent / "preflight.json").read_text(encoding="utf-8"))
    logs = json.loads(
        (PREPARATION / "log-preservation.closure-v1.json").read_text(encoding="utf-8")
    )
    preserved = {
        row["original_task_relative_path"]: TASK / row["preserved_task_relative_path"]
        for row in logs["files"]
    }
    preserved["task.json"] = PREPARATION / "task-before-closure.json"
    for name in ("implement", "check"):
        preserved[f"{name}.jsonl"] = (
            PREPARATION / "reference-adapters" / f"assessment-{name}.before-archive.jsonl.txt"
        )
    for row in preflight["initial_task_files"]:
        raw = preserved.get(row["path"], TASK / row["path"]).read_bytes()
        assert digest(raw) == row["sha256"] and len(raw) == row["size"], row["path"]
    mapping = json.loads(
        (PREPARATION / "reference-adapters/mapping.closure-v1.json").read_text(encoding="utf-8")
    )
    archived = TASK.relative_to(REPO).as_posix() == ARCHIVE_ROOT
    references = 0
    for manifest in mapping["manifests"]:
        adapter = TASK / manifest["adapter_task_relative_path"]
        assert digest(adapter.read_bytes()) == manifest["adapter_sha256"]
        old = manifest["source"]
        if old.startswith(OLD_ROOT + "/"):
            current = TASK / old.removeprefix(OLD_ROOT + "/")
            if archived:

                def parse(path: Path) -> list[dict]:
                    return [
                        json.loads(line)
                        for line in path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]

                assert parse(current) == parse(adapter), current.name
            else:
                assert digest(current.read_bytes()) == manifest["source_sha256"]
        else:
            assert digest((REPO / old).read_bytes()) == manifest["source_sha256"]
        for entry in manifest["entries"]:
            target = REPO / entry["new"]
            if entry["new"].startswith(ARCHIVE_ROOT + "/"):
                target = TASK / entry["new"].removeprefix(ARCHIVE_ROOT + "/")
            raw = target.read_bytes()
            assert digest(raw) == entry["target_sha256"] and len(raw) == entry["target_size"]
            references += 1
    print(
        json.dumps(
            {
                "mode": "verify",
                "archived": archived,
                "original_files_verified": len(preflight["initial_task_files"]),
                "log_copies_verified": len(logs["files"]),
                "reference_entries_verified": references,
                "writes": 0,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    if parser.parse_args().verify:
        verify_preserved()
        return
    preflight = json.loads((PREPARATION.parent / "preflight.json").read_text(encoding="utf-8"))
    original = preflight["initial_task_files"]
    assert len(original) == 463
    before_task = PREPARATION / "task-before-closure.json"
    if not before_task.exists():
        raw = (TASK / "task.json").read_bytes()
        expected = next(row for row in original if row["path"] == "task.json")
        assert digest(raw) == expected["sha256"] and len(raw) == expected["size"]
        preserve(before_task, raw)
    audited: list[dict] = []
    failures: list[dict] = []
    secret_candidates: list[dict] = []
    large_files: list[dict] = []
    for expected in original:
        relative = expected["path"]
        path = TASK / relative
        assert path.resolve().is_relative_to(TASK.resolve())
        raw = (before_task if relative == "task.json" else path).read_bytes()
        if digest(raw) != expected["sha256"] or len(raw) != expected["size"]:
            failures.append({"path": relative, "error": "preflight fingerprint mismatch"})
        if path.suffix not in ALLOWED or b"\x00" in raw:
            failures.append({"path": relative, "error": "unexpected type or NUL byte"})
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            failures.append({"path": relative, "error": "not UTF-8"})
            continue
        value = None
        try:
            if path.suffix == ".json":
                value = json.loads(text)
            elif path.suffix == ".jsonl":
                for line in text.splitlines():
                    if line.strip():
                        json.loads(line)
        except json.JSONDecodeError:
            failures.append({"path": relative, "error": "invalid JSON/JSONL"})
        for kind, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                secret_candidates.append(
                    {"path": relative, "kind": kind, "line": text[: match.start()].count("\n") + 1}
                )
        lines = text.splitlines()
        row = {
            "path": relative,
            "size": len(raw),
            "sha256": digest(raw),
            "purpose": purpose(relative),
            "utf8": True,
            "binary": False,
            "crlf_count": raw.count(b"\r\n"),
            "trailing_space_lines": [
                i for i, line in enumerate(lines, 1) if line.rstrip(" \t") != line
            ],
            "blank_at_eof": bool(lines and not lines[-1]),
        }
        audited.append(row)
        if len(raw) >= 1_000_000:
            assert isinstance(value, dict)
            large_files.append({**row, "structure": large_json_review(value)})
    audit = {
        "revision": "closure-v1",
        "tool_sha256": digest(Path(__file__).read_bytes()),
        "fixed_file_count": len(audited),
        "total_bytes": sum(row["size"] for row in audited),
        "suffix_counts": dict(sorted(Counter(Path(row["path"]).suffix for row in audited).items())),
        "failures": failures,
        "credential_candidates": secret_candidates,
        "large_file_count": len(large_files),
        "large_files": large_files,
        "files": audited,
        "private_directories_opened": False,
        "temporary_directories_opened": False,
        "limits": [
            "仅检查 preflight 固定的 463 个任务文件；并发新增收尾文件由独立终审覆盖。",
            "凭据模式检查是辅助检查，不能单独证明内容来源；合成来源另由生成器和观测标识审核。",
            "原始空白仅记录，不删除、不作为代码门槛通过证明。",
            "task.json 的历史字节从 task-before-closure.json 核对；本轮授权为单独新增字段。",
        ],
    }
    write_json(PREPARATION / "material-audit.closure-v1.json", audit)
    assert not failures and not secret_candidates, "Evidence review needs resolution before copying"
    ignored = preflight["ignored_task_files"]["stdout"].splitlines()
    assert len(ignored) == 38
    copies = []
    for old in ignored:
        assert old.startswith(OLD_ROOT + "/") and old.endswith(".log")
        relative = old.removeprefix(OLD_ROOT + "/")
        source = TASK / relative
        destination = PREPARATION / "logs" / (relative + ".txt")
        raw = source.read_bytes()
        preserve(destination, raw)
        check = subprocess.run(
            ["git", "check-ignore", "--no-index", "--", destination.relative_to(REPO).as_posix()],
            cwd=REPO,
            capture_output=True,
            check=False,
        )
        assert check.returncode == 1
        copies.append(
            {
                "original_task_relative_path": relative,
                "preserved_task_relative_path": destination.relative_to(TASK).as_posix(),
                "size": len(raw),
                "sha256": digest(raw),
                "original_mtime_ns": source.stat().st_mtime_ns,
                "byte_equal": destination.read_bytes() == raw,
                "git_check_ignore_exit": check.returncode,
            }
        )
    write_json(
        PREPARATION / "log-preservation.closure-v1.json",
        {
            "revision": "closure-v1",
            "count": len(copies),
            "files": copies,
            "meaning": "38 个原服务日志均为空；保留字节与路径，不用空日志证明服务退出。",
        },
    )
    mappings = []
    adapter_dir = PREPARATION / "reference-adapters"
    for owner, source_root in (("assessment", TASK), ("b1", REPO / B1_ROOT)):
        for name in ("implement", "check"):
            source = source_root / f"{name}.jsonl"
            raw = source.read_bytes()
            if owner == "assessment":
                preserve(adapter_dir / f"assessment-{name}.before-archive.jsonl.txt", raw)
            entries = [
                json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()
            ]
            changes = []
            for index, entry in enumerate(entries, 1):
                old = entry["file"]
                current = REPO / old
                if old.startswith(OLD_ROOT + "/"):
                    current = TASK / old.removeprefix(OLD_ROOT + "/")
                    entry["file"] = ARCHIVE_ROOT + old.removeprefix(OLD_ROOT)
                assert current.is_file()
                content = current.read_bytes()
                changes.append(
                    {
                        "line": index,
                        "old": old,
                        "new": entry["file"],
                        "changed": old != entry["file"],
                        "target_sha256": digest(content),
                        "target_size": len(content),
                    }
                )
            destination = adapter_dir / f"{owner}-{name}.closure-v1.jsonl"
            content = (
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n"
            ).encode("utf-8")
            preserve(destination, content)
            mappings.append(
                {
                    "source": source.relative_to(REPO).as_posix(),
                    "source_sha256": digest(raw),
                    "source_size": len(raw),
                    "adapter_task_relative_path": destination.relative_to(TASK).as_posix(),
                    "adapter_sha256": digest(content),
                    "adapter_size": len(content),
                    "entries": changes,
                }
            )
    write_json(
        adapter_dir / "mapping.closure-v1.json",
        {
            "revision": "closure-v1",
            "old_root": OLD_ROOT,
            "archive_root": ARCHIVE_ROOT,
            "activation": (
                "归档后显式使用 B1 适配清单；冻结原件保持。旧评估默认清单由主会话仅更新直接自引用。"
            ),
            "manifests": mappings,
        },
    )
    write_json(
        PREPARATION / "task-before-closure-fingerprint.json",
        {
            "source": OLD_ROOT + "/task.json",
            "copy": before_task.relative_to(TASK).as_posix(),
            "sha256": digest(before_task.read_bytes()),
            "size": before_task.stat().st_size,
            "matches_preflight": True,
            "captured_before_authorization_metadata_edit": True,
        },
    )
    print(
        json.dumps(
            {
                "audited": len(audited),
                "errors": len(failures),
                "credential_candidates": len(secret_candidates),
                "large_files": len(large_files),
                "logs": len(copies),
                "adapters": len(mappings),
            }
        )
    )


if __name__ == "__main__":
    main()
