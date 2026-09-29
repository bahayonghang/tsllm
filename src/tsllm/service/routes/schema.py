"""Run configuration JSON Schema for form rendering."""

from typing import Any

from fastapi import APIRouter

from tsllm.config.schema import run_config_schema

router = APIRouter(tags=["schema"])


@router.get("/schema/run-config")
def run_config() -> dict[str, Any]:
    """`run_config` is the RunConfig schema; `backbone_options` maps backbone to Options schema."""
    return run_config_schema()
