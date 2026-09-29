"""Reporter that appends run events to events.jsonl."""

import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

from tsllm.config.io import json_safe
from tsllm.reporting import LogLevel, Reporter


class FileReporter:
    """Write one JSON line per event. An optional mirror receives the same calls."""

    def __init__(self, path: Path, mirror: Reporter | None = None) -> None:
        self.path = path
        self.mirror = mirror
        self._stage: str | None = None
        self._last_progress = float("-inf")

    def _write(self, kind: str, **payload: Any) -> None:
        event = {"ts": datetime.now(UTC).isoformat(), "kind": kind, **payload}
        line = json.dumps(json_safe(event), ensure_ascii=False, allow_nan=False)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()

    def log(self, msg: str, level: LogLevel = "info") -> None:
        self._write("log", level=level, msg=msg)
        if self.mirror is not None:
            self.mirror.log(msg, level)

    def progress(self, step: int, total: int) -> None:
        now = monotonic()
        if step != total and now - self._last_progress < 0.5:
            return
        self._last_progress = now
        self._write("progress", stage=self._stage, step=step, total=total)
        if self.mirror is not None:
            self.mirror.progress(step, total)

    def metric(self, name: str, value: float, step: int | None = None) -> None:
        self._write("metric", name=name, value=value, step=step)
        if self.mirror is not None:
            self.mirror.metric(name, value, step)

    def stage(self, name: str) -> None:
        self._stage = name
        self._last_progress = float("-inf")
        self._write("stage", name=name)
        if self.mirror is not None:
            self.mirror.stage(name)
