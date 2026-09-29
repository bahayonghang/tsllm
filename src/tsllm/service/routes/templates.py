"""Run configuration templates."""

from typing import Annotated

from fastapi import APIRouter, Path

from tsllm.config.run import RunConfig
from tsllm.config.templates import (
    TEMPLATE_NAME_PATTERN,
    list_templates,
    load_template,
    save_template,
)
from tsllm.service.deps import SettingsDep
from tsllm.service.models import TemplateOut

router = APIRouter(tags=["templates"])

TemplateName = Annotated[str, Path(pattern=TEMPLATE_NAME_PATTERN)]


@router.get("/run-templates")
def templates(settings: SettingsDep) -> list[TemplateOut]:
    return [TemplateOut(name=name) for name in list_templates(settings.templates_dir)]


@router.get("/run-templates/{name}")
def get_template(name: TemplateName, settings: SettingsDep) -> RunConfig:
    return load_template(name, settings.templates_dir)


@router.put("/run-templates/{name}")
def put_template(name: TemplateName, cfg: RunConfig, settings: SettingsDep) -> RunConfig:
    save_template(name, cfg, settings.templates_dir)
    return cfg
