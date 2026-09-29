"""Atomic prepared-data cache with configuration and source freshness checks."""

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any, ClassVar, Literal
from uuid import uuid4

import polars as pl

from tsllm.config.dataset import DatasetConfig
from tsllm.data.profile import build_meta
from tsllm.data.registry import DatasetConfigError
from tsllm.data.types import PreparedFrame
from tsllm.errors import TsllmError


class DatasetNotIngested(TsllmError):
    code: ClassVar[str] = "DATASET_NOT_INGESTED"


def config_hash(cfg: DatasetConfig) -> str:
    payload = cfg.model_dump(mode="json", exclude={"id"})
    if cfg.channels is not None:
        payload["channels"] = [{"name": ch.name, "role": ch.role} for ch in cfg.channels]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:12]


def default_cache_root() -> Path:
    """Dataset cache root; the service sets TSLLM_CACHE_DIR for its worker subprocesses."""
    return Path(os.environ.get("TSLLM_CACHE_DIR", "cache")) / "datasets"


def cache_dir(cfg: DatasetConfig, root: Path | None = None) -> Path:
    return (root if root is not None else default_cache_root()) / cfg.id / config_hash(cfg)


def source_fingerprint(cfg: DatasetConfig) -> dict[str, int]:
    stat = cfg.source.path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _read_meta(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError("cache metadata must be an object")
    return payload


def is_fresh(cfg: DatasetConfig, root: Path | None = None) -> bool:
    directory = cache_dir(cfg, root)
    try:
        meta = _read_meta(directory / "meta.json")
        return (
            (directory / "frame.parquet").is_file()
            and meta.get("config_hash") == config_hash(cfg)
            and meta.get("source") == source_fingerprint(cfg)
        )
    except (OSError, ValueError, UnicodeError):
        return False


def cache_status(
    cfg: DatasetConfig, root: Path | None = None
) -> Literal["fresh", "stale", "missing"]:
    """Missing means that no cache of any configuration exists for the dataset id."""
    if is_fresh(cfg, root):
        return "fresh"
    dataset_root = cache_dir(cfg, root).parent
    return "stale" if any(dataset_root.glob("*/meta.json")) else "missing"


def read_meta(cfg: DatasetConfig, root: Path | None = None) -> dict[str, Any] | None:
    """Metadata of a fresh cache, or None. The frame is not read."""
    if not is_fresh(cfg, root):
        return None
    try:
        return _read_meta(cache_dir(cfg, root) / "meta.json")
    except (OSError, ValueError, UnicodeError):
        return None


def write_cache(
    cfg: DatasetConfig, prepared: PreparedFrame, root: Path | None = None
) -> PreparedFrame:
    directory = cache_dir(cfg, root)
    token = uuid4().hex
    frame_tmp = directory / f"frame.{token}.tmp"
    meta_tmp = directory / f"meta.{token}.tmp"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        meta = build_meta(prepared, cfg) | {
            "config_hash": config_hash(cfg),
            "source": source_fingerprint(cfg),
        }
        prepared.frame.write_parquet(frame_tmp)
        with meta_tmp.open("w", encoding="utf-8") as stream:
            json.dump(meta, stream, ensure_ascii=False, allow_nan=False, indent=2)
        # Metadata is the completion marker. A failed rewrite must not retain a fresh marker.
        (directory / "meta.json").unlink(missing_ok=True)
        os.replace(frame_tmp, directory / "frame.parquet")
        os.replace(meta_tmp, directory / "meta.json")
    except (OSError, pl.exceptions.PolarsError, ValueError):
        raise DatasetConfigError(f"dataset '{cfg.id}' cache cannot be written") from None
    finally:
        frame_tmp.unlink(missing_ok=True)
        meta_tmp.unlink(missing_ok=True)
    return replace(prepared, meta=meta)


def read_cache(cfg: DatasetConfig, root: Path | None = None) -> PreparedFrame:
    if not is_fresh(cfg, root):
        raise DatasetNotIngested(f"dataset '{cfg.id}' cache is missing or stale")
    directory = cache_dir(cfg, root)
    try:
        meta = _read_meta(directory / "meta.json")
        frame = pl.read_parquet(directory / "frame.parquet")
        return PreparedFrame(frame, meta["channel_names"], cfg.freq, meta)
    except (OSError, ValueError, KeyError, pl.exceptions.PolarsError):
        raise DatasetNotIngested(f"dataset '{cfg.id}' cache cannot be read") from None
