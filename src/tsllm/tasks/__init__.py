"""Task pipelines. Importing this package registers all task types."""

from tsllm.tasks import classify, forecast  # noqa: F401
from tsllm.tasks.context import TaskContext
from tsllm.tasks.registry import get_task, register_task

__all__ = ["TaskContext", "get_task", "register_task"]
