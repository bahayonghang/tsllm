"""YAML-backed dataset registry."""

import re
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import ValidationError

from tsllm.config.dataset import DatasetConfig
from tsllm.config.io import load_yaml
from tsllm.errors import TsllmError


class DatasetNotFound(TsllmError):
    code: ClassVar[str] = "DATASET_NOT_FOUND"


class DatasetConfigError(TsllmError):
    code: ClassVar[str] = "DATASET_CONFIG_INVALID"


def dataset_dir() -> Path:
    return Path("configs/datasets")


def load_dataset(dataset_id: str, directory: Path | None = None) -> DatasetConfig:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", dataset_id) is None:
        raise DatasetConfigError("dataset id is invalid")
    path = (directory if directory is not None else dataset_dir()) / f"{dataset_id}.yaml"
    if not path.is_file():
        raise DatasetNotFound(f"dataset '{dataset_id}' was not found")
    try:
        cfg = load_yaml(DatasetConfig, path)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError):
        # YAML and validation exceptions can contain source values.
        raise DatasetConfigError(f"dataset '{dataset_id}' has an invalid configuration") from None
    if cfg.id != dataset_id:
        raise DatasetConfigError(f"dataset '{dataset_id}' id does not match its file name")
    return cfg


def list_datasets(directory: Path | None = None) -> list[DatasetConfig]:
    root = directory if directory is not None else dataset_dir()
    return [load_dataset(path.stem, root) for path in sorted(root.glob("*.yaml"))]
