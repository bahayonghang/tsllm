"""Shared domain error base."""

from typing import ClassVar


class TsllmError(Exception):
    code: ClassVar[str] = "TSLLM_ERROR"
