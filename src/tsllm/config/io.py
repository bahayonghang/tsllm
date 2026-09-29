"""UTF-8 YAML configuration IO."""

from pathlib import Path

import yaml
from pydantic import BaseModel


def load_yaml[T: BaseModel](model: type[T], path: Path) -> T:
    with path.open(encoding="utf-8") as stream:
        return model.model_validate(yaml.safe_load(stream))


def dump_yaml(model: BaseModel, path: Path) -> None:
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(model.model_dump(mode="json"), stream, allow_unicode=True, sort_keys=False)
