"""Backbone registry contents."""

from fastapi import APIRouter

from tsllm.backbones import list_backbones
from tsllm.backbones.registry import BackboneInfo

router = APIRouter(tags=["backbones"])


@router.get("/backbones")
def backbones() -> list[BackboneInfo]:
    return list_backbones()
