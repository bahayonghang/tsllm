"""Run submission, status, cancel, events, and results."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse

from tsllm.config.run import EvalSplit, JobSpec, RunConfig
from tsllm.data.registry import load_dataset
from tsllm.runs.results import prediction_origins, prediction_rows, read_env, read_metrics
from tsllm.runs.store import TERMINAL_STATES, RunStatus, RunSummary
from tsllm.service.deps import JobsDep, SettingsDep, StoreDep
from tsllm.service.models import PredictionsOut, RunDetailOut, RunSubmittedOut
from tsllm.service.sse import tail_events
from tsllm.tasks.validation import validate_job

router = APIRouter(tags=["runs"])


@router.get("/runs")
def runs(store: StoreDep) -> list[RunSummary]:
    return store.list()


@router.post("/runs", status_code=201)
async def submit(
    cfg: RunConfig, settings: SettingsDep, store: StoreDep, jobs: JobsDep
) -> RunSubmittedOut:
    job = JobSpec(
        kind="experiment", dataset=load_dataset(cfg.dataset, settings.datasets_dir), run=cfg
    )
    validate_job(job, settings.dataset_cache_root)
    run_id = await jobs.submit(job)
    return RunSubmittedOut(run_id=run_id, status=store.read_status(run_id))


@router.get("/runs/{run_id}")
def run(run_id: str, store: StoreDep) -> RunDetailOut:
    return RunDetailOut(
        run_id=run_id,
        job=store.read_job(run_id),
        status=store.read_status(run_id),
        env=read_env(store, run_id),
    )


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str, jobs: JobsDep) -> RunStatus:
    return await jobs.cancel(run_id)


@router.get(
    "/runs/{run_id}/events",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def events(
    run_id: str,
    store: StoreDep,
    settings: SettingsDep,
    last_event_id: Annotated[int | None, Header(ge=0)] = None,
    from_: Annotated[int | None, Query(alias="from", ge=0)] = None,
) -> StreamingResponse:
    """SSE of events.jsonl. Event ids are line numbers; the stream starts after the given id."""
    path = store.path(run_id) / "events.jsonl"

    def terminal_state() -> str | None:
        state = store.read_status(run_id).state
        return state if state in TERMINAL_STATES else None

    start = last_event_id if last_event_id is not None else from_ or 0
    stream = tail_events(
        path,
        start,
        terminal_state,
        poll_seconds=settings.poll_seconds,
        heartbeat_seconds=settings.heartbeat_seconds,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}/metrics")
def metrics(run_id: str, store: StoreDep) -> dict[str, Any]:
    """metrics.json of the run; see the parent design section 6.1."""
    return read_metrics(store, run_id)


@router.get("/runs/{run_id}/predictions")
def predictions(
    run_id: str,
    split: EvalSplit,
    store: StoreDep,
    channel: str | None = None,
    origin_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> PredictionsOut:
    """Without origin_time: the thinned origin list. With origin_time: the rows of that origin."""
    if origin_time is None:
        origins, total = prediction_origins(store, run_id, split, limit)
        return PredictionsOut(
            split=split, origin_time=None, origins=origins, total_origins=total, rows=None
        )
    rows = prediction_rows(store, run_id, split, origin_time, channel)
    return PredictionsOut(
        split=split, origin_time=origin_time, origins=None, total_origins=None, rows=rows
    )
