"""Metric comparison of several runs."""

from typing import Annotated

from fastapi import APIRouter, Query

from tsllm.runs.compare import compare_runs
from tsllm.service.deps import StoreDep
from tsllm.service.models import CompareOut

router = APIRouter(tags=["compare"])


@router.get("/compare")
def compare(
    run_ids: Annotated[str, Query(pattern=r"^[A-Za-z0-9_.-]+(,[A-Za-z0-9_.-]+)*$")],
    store: StoreDep,
) -> CompareOut:
    """`run_ids` is a comma-separated list of run ids."""
    return CompareOut.model_validate(compare_runs(store, list(dict.fromkeys(run_ids.split(",")))))
