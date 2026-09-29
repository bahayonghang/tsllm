"""Shared adapter contract, checkpoint resolution, and import boundaries."""

import builtins
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

import pytest
from pydantic import ValidationError

from tsllm.backbones.base import Backbone, BackboneLoadError, Capabilities, CapabilityError
from tsllm.backbones.checkpoint import resolve_checkpoint
from tsllm.backbones.registry import get_backbone, list_backbones
from tsllm.config.backbone import BackboneConfig, FinetuneConfig, LoraSpec
from tsllm.data.stats import FitStats
from tsllm.data.types import SegmentSet
from tsllm.reporting import NullReporter

from .conftest import RecordingReporter, context


def test_registry_import_is_light() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, json; import tsllm.backbones as b; "
            "json.dumps([x.model_dump(mode='json') for x in b.list_backbones()]); "
            "assert not {'torch','chronos','transformers','tsfm_public','peft','sklearn'} "
            "& sys.modules.keys()",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    json.dumps([info.model_dump(mode="json") for info in list_backbones()])
    with pytest.raises(BackboneLoadError):
        get_backbone("unknown-backbone")


def test_config_validation() -> None:
    assert BackboneConfig(name="test", device="cpu", dtype="bf16").dtype == "fp32"
    for cls, values in [
        (BackboneConfig, {"name": "test", "mode": "lora"}),
        (FinetuneConfig, {"mode": "lora"}),
        (FinetuneConfig, {"num_steps": 0}),
        (LoraSpec, {"r": 0}),
    ]:
        with pytest.raises(ValidationError):
            cls.model_validate(values)


def test_reporter_and_capability_contract() -> None:
    class Sample(Backbone):
        name: ClassVar[str] = "sample"
        capabilities: ClassVar[Capabilities] = Capabilities(
            forecast_modes=set(), embed=False, quantiles=False, multivariate="none"
        )

    reporter = NullReporter()
    model = Sample()
    model.load(BackboneConfig(name="sample"), None, reporter=reporter)
    assert model.reporter is reporter
    with pytest.raises(CapabilityError, match="lora"):
        model._check_mode("lora")


def test_local_checkpoint(tmp_path: Path) -> None:
    result = resolve_checkpoint(BackboneConfig(name="test", checkpoint=str(tmp_path)))
    assert result.path == tmp_path.resolve()
    assert result.source == "local"
    assert result.revision is None
    with pytest.raises(BackboneLoadError):
        resolve_checkpoint(BackboneConfig(name="test", checkpoint=str(tmp_path / "absent")))


def test_hf_checkpoint_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import huggingface_hub

    calls = []

    def download(*, repo_id: str, revision: str | None) -> str:
        calls.append((repo_id, revision))
        return str(tmp_path / "snapshots" / "resolved-commit")

    monkeypatch.setattr(huggingface_hub, "snapshot_download", download)
    result = resolve_checkpoint(
        BackboneConfig(name="test", checkpoint="owner/model", revision="pinned-commit")
    )
    assert calls == [("owner/model", "pinned-commit")]
    assert result.revision == "resolved-commit"
    assert result.source == "huggingface"


def test_hub_environment_and_offline_resolution(tmp_path: Path) -> None:
    code = "\n".join(
        [
            "import os, socket",
            "from huggingface_hub import constants",
            "from huggingface_hub.errors import LocalEntryNotFoundError",
            "from tsllm.backbones.checkpoint import resolve_checkpoint",
            "from tsllm.backbones.base import BackboneLoadError",
            "from tsllm.config.backbone import BackboneConfig",
            "assert constants.ENDPOINT == os.environ['HF_ENDPOINT']",
            "assert constants.HF_HUB_OFFLINE",
            "def no_network(*args, **kwargs):",
            "    raise AssertionError('offline resolution attempted network access')",
            "socket.socket.connect = no_network",
            "try:",
            "    resolve_checkpoint(BackboneConfig(name='test', checkpoint='synthetic/uncached'))",
            "except BackboneLoadError as exc:",
            "    assert isinstance(exc.__cause__, LocalEntryNotFoundError)",
            "else:",
            "    raise AssertionError('an uncached offline checkpoint must fail')",
        ]
    )
    env = {
        **os.environ,
        "HF_ENDPOINT": "https://mirror.example.invalid",
        "HF_HUB_OFFLINE": "1",
        "HF_HOME": str(tmp_path),
        "HF_HUB_CACHE": str(tmp_path / "hub"),
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", ["chronos2", "timesfm25", "ttm"])
def test_invalid_model_checkpoint_is_domain_error(
    name: str,
    tmp_path: Path,
    unit_stats: FitStats,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
) -> None:
    model = get_backbone(name)
    with pytest.raises(BackboneLoadError):
        model.load(
            BackboneConfig(name=name, checkpoint=str(tmp_path), device="cpu"),
            unit_stats,
            reporter=reporter,
        )
        model.forecast(context(sine_segments.arrays[0][None, :, :32]), 8)


@pytest.mark.parametrize(
    "name,dependency",
    [("chronos2", "chronos"), ("timesfm25", "transformers"), ("ttm", "tsfm_public")],
)
def test_missing_model_dependency_is_domain_error(
    name: str,
    dependency: str,
    tmp_path: Path,
    unit_stats: FitStats,
    sine_segments: SegmentSet,
    reporter: RecordingReporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = builtins.__import__

    def unavailable(module: str, *args: Any, **kwargs: Any) -> Any:
        if module.split(".")[0] == dependency:
            raise ImportError("synthetic unavailable dependency")
        return original(module, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    model = get_backbone(name)
    with pytest.raises(BackboneLoadError, match=name):
        model.load(
            BackboneConfig(name=name, checkpoint=str(tmp_path), device="cpu"),
            unit_stats,
            reporter=reporter,
        )
        model.forecast(context(sine_segments.arrays[0][None, :, :32]), 8)
