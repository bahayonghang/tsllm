"""Resolve checkpoints through Hugging Face or a local directory."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tsllm.backbones.base import BackboneLoadError
from tsllm.config.backbone import BackboneConfig


@dataclass(frozen=True)
class ResolvedCheckpoint:
    path: Path
    revision: str | None
    source: Literal["local", "huggingface"]


@contextmanager
def checkpoint_loading(name: str, checkpoint: str | Path) -> Iterator[None]:
    """Translate model-library load failures at the adapter boundary."""
    try:
        yield
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        raise BackboneLoadError(
            f"backbone '{name}' could not load checkpoint '{checkpoint}' ({type(exc).__name__})"
        ) from None


def resolve_checkpoint(cfg: BackboneConfig) -> ResolvedCheckpoint:
    checkpoint = cfg.checkpoint
    if not checkpoint:
        raise BackboneLoadError(f"backbone '{cfg.name}' requires a checkpoint")
    path = Path(checkpoint).expanduser()
    if path.is_dir():
        path = path.resolve()
        revision = path.name if path.parent.name == "snapshots" else cfg.revision
        return ResolvedCheckpoint(path, revision, "local")
    if path.exists() or path.is_absolute() or checkpoint.startswith("."):
        raise BackboneLoadError(f"checkpoint '{checkpoint}' is not a local directory")
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import HfHubHTTPError, HFValidationError, LocalEntryNotFoundError

    try:
        path = Path(snapshot_download(repo_id=checkpoint, revision=cfg.revision))
    except (OSError, HFValidationError, HfHubHTTPError, LocalEntryNotFoundError) as exc:
        raise BackboneLoadError(f"checkpoint '{checkpoint}' could not be resolved") from exc
    return ResolvedCheckpoint(path, path.name, "huggingface")
