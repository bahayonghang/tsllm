"""Run configuration templates in configs/runs/<name>.yaml."""

import re
from pathlib import Path
from typing import ClassVar

from tsllm.config.io import dump_yaml, load_yaml
from tsllm.config.run import RunConfig
from tsllm.errors import TsllmError

TEMPLATE_NAME_PATTERN = r"^[A-Za-z0-9_-]+$"


class TemplateNotFound(TsllmError):
    code: ClassVar[str] = "TEMPLATE_NOT_FOUND"


def _path(name: str, directory: Path) -> Path:
    if re.fullmatch(TEMPLATE_NAME_PATTERN, name) is None:
        raise TemplateNotFound(f"template '{name}' was not found")
    return directory / f"{name}.yaml"


def list_templates(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(
        path.stem
        for path in directory.glob("*.yaml")
        if re.fullmatch(TEMPLATE_NAME_PATTERN, path.stem) is not None
    )


def load_template(name: str, directory: Path) -> RunConfig:
    path = _path(name, directory)
    if not path.is_file():
        raise TemplateNotFound(f"template '{name}' was not found")
    return load_yaml(RunConfig, path)


def save_template(name: str, cfg: RunConfig, directory: Path) -> None:
    path = _path(name, directory)
    directory.mkdir(parents=True, exist_ok=True)
    dump_yaml(cfg, path)
