"""Server-sent events from an append-only events.jsonl file."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from time import monotonic


class _LineReader:
    """Reads complete new lines. The file offset is kept, so each byte is read once."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0

    def read(self) -> list[str]:
        if not self.path.is_file():
            return []
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            data = stream.read()
        end = data.rfind(b"\n") + 1
        # A line without its newline is still being written; it is read next time.
        self.offset += end
        # str.splitlines also splits at U+2028, which JSON text can contain unescaped.
        return data[:end].decode("utf-8").split("\n")[:-1]


def _kind(line: str) -> str:
    try:
        kind = json.loads(line).get("kind")
    except (ValueError, AttributeError):
        return "log"
    return kind if isinstance(kind, str) else "log"


async def tail_events(
    path: Path,
    start_line: int,
    terminal_state: Callable[[], str | None],
    *,
    poll_seconds: float,
    heartbeat_seconds: float,
) -> AsyncIterator[str]:
    """Send lines after start_line (1-based ids), then `end` once the run is terminal.

    The state is read before the file. A terminal state means that the worker has written
    its last event, so an empty read after it means that the stream is complete.
    """
    reader = _LineReader(path)
    line_no = 0
    last_sent = monotonic()
    while True:
        state = terminal_state()
        lines = reader.read()
        for line in lines:
            line_no += 1
            if line_no > start_line:
                yield f"id: {line_no}\nevent: {_kind(line)}\ndata: {line}\n\n"
                last_sent = monotonic()
        if lines:
            continue
        if state is not None:
            yield f"event: end\ndata: {json.dumps({'state': state})}\n\n"
            return
        if monotonic() - last_sent >= heartbeat_seconds:
            yield ": ping\n\n"
            last_sent = monotonic()
        await asyncio.sleep(poll_seconds)
