"""Job queue: worker subprocesses in a gpu and a cpu pool, cancel, and restart recovery."""

import asyncio
import logging
import os
import subprocess
from collections.abc import Coroutine
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal

import psutil

from tsllm.config.run import JobSpec
from tsllm.runs.store import TERMINAL_STATES, InvalidTransition, RunNotFound, RunStatus, RunStore
from tsllm.service.settings import Settings

logger = logging.getLogger(__name__)

Pool = Literal["gpu", "cpu"]
Handle = subprocess.Popen[bytes] | psutil.Process


def pool_for(job: JobSpec) -> Pool:
    return "gpu" if job.run is not None and job.run.backbone.device == "cuda" else "cpu"


def _live_worker(pid: int | None, run_dir: Path) -> psutil.Process | None:
    """The process of pid when its command line runs the worker for run_dir."""
    if pid is None:
        return None
    try:
        process = psutil.Process(pid)
        cmdline = process.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None
    target = run_dir.resolve()
    if "tsllm.runs.worker" in cmdline and any(_same_path(arg, target) for arg in cmdline):
        return process
    return None


def _same_path(arg: str, target: Path) -> bool:
    try:
        return Path(arg).resolve() == target
    except (OSError, ValueError):
        return False


def _exited(handle: Handle) -> tuple[bool, int | None]:
    if isinstance(handle, subprocess.Popen):
        code = handle.poll()
        return code is not None, code
    try:
        return not handle.is_running() or handle.status() == psutil.STATUS_ZOMBIE, None
    except psutil.NoSuchProcess:
        return True, None


def terminate_tree(pid: int, timeout: float = 3.0) -> None:
    """Terminate a process and its children; kill those still alive after timeout."""
    try:
        parent = psutil.Process(pid)
        processes = [*parent.children(recursive=True), parent]
    except psutil.NoSuchProcess:
        return
    for process in processes:
        with suppress(psutil.NoSuchProcess):
            process.terminate()
    _, alive = psutil.wait_procs(processes, timeout=timeout)
    for process in alive:
        with suppress(psutil.NoSuchProcess):
            process.kill()
    psutil.wait_procs(alive, timeout=timeout)


class JobManager:
    """Schedules queued runs. Every state write by the service holds one lock.

    The worker writes its own transitions. The service writes a transition that can race
    with the worker (cancel, failed after exit) only after the worker process has ended.
    """

    def __init__(self, store: RunStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings
        self._queues: dict[Pool, asyncio.Queue[str]] = {
            "gpu": asyncio.Queue(),
            "cpu": asyncio.Queue(),
        }
        self._lock = asyncio.Lock()
        self._handles: dict[str, Handle] = {}
        self._cancelling: set[str] = set()
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        self._recover()
        slots: dict[Pool, int] = {"gpu": self._settings.gpu_slots, "cpu": self._settings.cpu_slots}
        for pool, count in slots.items():
            for _ in range(count):
                self._spawn(self._runner(pool))

    async def stop(self) -> None:
        """Stop scheduling. Running worker processes continue; a restart reattaches them."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def submit(self, job: JobSpec) -> str:
        run_id = self._store.create(job)
        self._queues[pool_for(job)].put_nowait(run_id)
        logger.info("run %s queued", run_id)
        return run_id

    async def cancel(self, run_id: str) -> RunStatus:
        async with self._lock:
            status = self._store.read_status(run_id)
            handle = self._handles.get(run_id)
            if handle is None or status.state in TERMINAL_STATES:
                # No worker process: a queued run waits in a queue and is skipped there.
                return self._store.transition(run_id, "cancelled", writer="service")
            self._cancelling.add(run_id)
        try:
            await asyncio.to_thread(terminate_tree, handle.pid)
            async with self._lock:
                status = self._store.transition(run_id, "cancelled", writer="service")
        finally:
            self._cancelling.discard(run_id)
        logger.info("run %s cancelled", run_id)
        return status

    def pid(self, run_id: str) -> int | None:
        handle = self._handles.get(run_id)
        return None if handle is None else handle.pid

    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _recover(self) -> None:
        queued = []
        for summary in self._store.list():
            if summary.state == "queued":
                queued.append((summary.created_at, summary.run_id))
            elif summary.state == "running":
                status = self._store.read_status(summary.run_id)
                process = _live_worker(status.pid, self._store.path(summary.run_id))
                if process is None:
                    self._store.transition(
                        summary.run_id,
                        "interrupted",
                        writer="service",
                        error="no live worker process at service start",
                    )
                    logger.warning("run %s interrupted", summary.run_id)
                else:
                    self._handles[summary.run_id] = process
                    self._spawn(self._watch(summary.run_id, process))
                    logger.info("run %s reattached to pid %s", summary.run_id, process.pid)
        for _, run_id in sorted(queued):
            self._queues[pool_for(self._store.read_job(run_id))].put_nowait(run_id)
            logger.info("run %s queued again", run_id)

    async def _runner(self, pool: Pool) -> None:
        queue = self._queues[pool]
        while True:
            run_id = await queue.get()
            async with self._lock:
                handle = self._launch(run_id)
            if handle is not None:
                await self._watch(run_id, handle)

    def _launch(self, run_id: str) -> subprocess.Popen[bytes] | None:
        try:
            if self._store.read_status(run_id).state != "queued":
                return None
            run_dir = self._store.path(run_id).resolve()
        except RunNotFound:
            return None
        env = os.environ | {
            "TSLLM_CACHE_DIR": str(self._settings.cache_dir.resolve()),
            "PYTHONIOENCODING": "utf-8",
        }
        with (run_dir / "worker.log").open("ab") as log:
            process = subprocess.Popen(
                [*self._settings.worker_command, str(run_dir)],
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=env,
            )
        self._handles[run_id] = process
        logger.info("run %s started with pid %s", run_id, process.pid)
        return process

    async def _watch(self, run_id: str, handle: Handle) -> None:
        while True:
            exited, code = _exited(handle)
            if exited:
                break
            await asyncio.sleep(self._settings.poll_seconds)
        async with self._lock:
            self._handles.pop(run_id, None)
            if run_id in self._cancelling:
                return
            try:
                status = self._store.read_status(run_id)
                if status.state in ("queued", "running"):
                    # The worker ended without a final state, so no worker write can follow.
                    error = f"worker exited with code {code if code is not None else 'unknown'}"
                    if status.state == "queued":
                        error += " before it started"
                    status = self._store.transition(run_id, "failed", writer="service", error=error)
            except (RunNotFound, InvalidTransition):
                logger.exception("run %s: exit state cannot be recorded", run_id)
                return
        if status.state == "failed":
            logger.error("run %s failed: %s", run_id, status.error)
        else:
            logger.info("run %s finished: %s", run_id, status.state)
