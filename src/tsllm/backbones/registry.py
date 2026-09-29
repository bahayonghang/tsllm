"""Backbone discovery without importing model libraries."""

from collections.abc import Callable
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any

from tsllm.backbones.base import Backbone, BackboneLoadError, Capabilities
from tsllm.config.base import StrictModel


class BackboneInfo(StrictModel):
    name: str
    capabilities: Capabilities
    options_schema: dict[str, Any]
    requires: list[str]
    installed: bool
    default_checkpoint: str | None
    license: str | None
    license_url: str | None


@dataclass(frozen=True)
class Registration:
    cls: type[Backbone]
    requires: list[str]
    default_checkpoint: str | None
    license: str | None
    license_url: str | None


_REGISTRY: dict[str, Registration] = {}


def register_backbone[T: type[Backbone]](
    *,
    requires: list[str] | None = None,
    default_checkpoint: str | None = None,
    license: str | None = None,
    license_url: str | None = None,
) -> Callable[[T], T]:
    def register(cls: T) -> T:
        if cls.name in _REGISTRY:
            raise ValueError(f"backbone '{cls.name}' is already registered")
        _REGISTRY[cls.name] = Registration(
            cls, list(requires or []), default_checkpoint, license, license_url
        )
        return cls

    return register


def get_backbone(name: str) -> Backbone:
    if name not in _REGISTRY:
        raise BackboneLoadError(f"backbone '{name}' is not registered")
    return _REGISTRY[name].cls()


def list_backbones() -> list[BackboneInfo]:
    return [
        BackboneInfo(
            name=name,
            capabilities=entry.cls.capabilities,
            options_schema=entry.cls.Options.model_json_schema(),
            requires=entry.requires,
            installed=all(find_spec(module) is not None for module in entry.requires),
            default_checkpoint=entry.default_checkpoint,
            license=entry.license,
            license_url=entry.license_url,
        )
        for name, entry in sorted(_REGISTRY.items())
    ]
