"""UTF-8 YAML and JSON file IO."""

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel


def load_yaml[T: BaseModel](model: type[T], path: Path) -> T:
    with path.open(encoding="utf-8") as stream:
        return model.model_validate(yaml.safe_load(stream))


def dump_yaml(model: BaseModel | dict[str, Any], path: Path) -> None:
    payload = model.model_dump(mode="json") if isinstance(model, BaseModel) else model
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(payload, stream, allow_unicode=True, sort_keys=False)


def json_safe(value: Any) -> Any:
    """Convert numpy values to Python values and non-finite floats to null."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def dump_json(payload: Any, path: Path) -> None:
    """Write JSON atomically so that a concurrent reader sees the old or the new file."""
    tmp = path.with_name(f"{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(json_safe(payload), stream, ensure_ascii=False, allow_nan=False, indent=2)
    os.replace(tmp, path)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)
