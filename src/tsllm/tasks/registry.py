"""Task functions keyed by task.type."""

from collections.abc import Callable
from typing import Any

from tsllm.tasks.context import TaskContext

TaskFn = Callable[[TaskContext], dict[str, Any]]

_TASKS: dict[str, TaskFn] = {}


def register_task(task_type: str) -> Callable[[TaskFn], TaskFn]:
    def register(fn: TaskFn) -> TaskFn:
        if task_type in _TASKS:
            raise ValueError(f"task '{task_type}' is already registered")
        _TASKS[task_type] = fn
        return fn

    return register


def get_task(task_type: str) -> TaskFn:
    if task_type not in _TASKS:
        raise KeyError(f"task '{task_type}' is not registered")
    return _TASKS[task_type]
