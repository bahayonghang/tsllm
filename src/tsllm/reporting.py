"""Progress reporting shared by CLI and worker code."""

from time import monotonic
from typing import Literal, Protocol

import typer

LogLevel = Literal["debug", "info", "warning", "error"]


class Reporter(Protocol):
    def log(self, msg: str, level: LogLevel = "info") -> None: ...
    def progress(self, step: int, total: int) -> None: ...
    def metric(self, name: str, value: float, step: int | None = None) -> None: ...
    def stage(self, name: str) -> None: ...


class NullReporter:
    def log(self, msg: str, level: LogLevel = "info") -> None:
        pass

    def progress(self, step: int, total: int) -> None:
        pass

    def metric(self, name: str, value: float, step: int | None = None) -> None:
        pass

    def stage(self, name: str) -> None:
        pass


class PrintReporter:
    def __init__(self) -> None:
        self._last_progress = float("-inf")

    def log(self, msg: str, level: LogLevel = "info") -> None:
        typer.echo(f"[{level}] {msg}")

    def progress(self, step: int, total: int) -> None:
        now = monotonic()
        if step == total or now - self._last_progress >= 0.5:
            typer.echo(f"{step}/{total}")
            self._last_progress = now

    def metric(self, name: str, value: float, step: int | None = None) -> None:
        suffix = "" if step is None else f" step={step}"
        typer.echo(f"{name}={value}{suffix}")

    def stage(self, name: str) -> None:
        self._last_progress = float("-inf")
        typer.echo(f"[{name}]")
