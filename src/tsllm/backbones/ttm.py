"""Apache-2.0 Granite TTM with FitStats scaling and forward/backward context fill.

Remaining NaN becomes zero after scaling. Loading is deferred until L and H are
known. Native context cropping/padding is reported and remains inside the library.
"""

import json
from importlib import resources
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field

from tsllm.backbones.base import (
    Backbone,
    BackboneLoadError,
    Capabilities,
    CapabilityError,
    FinetuneMode,
    ForecastOutput,
)
from tsllm.backbones.checkpoint import checkpoint_loading, resolve_checkpoint
from tsllm.backbones.nan import ffill_bfill, fit_scaling
from tsllm.backbones.registry import register_backbone
from tsllm.backbones.training import autocast, torch_dtype, train_model
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.config.base import StrictModel
from tsllm.data.stats import FitStats
from tsllm.data.types import ContextBatch, SegmentSet
from tsllm.reporting import Reporter

DEFAULT_CHECKPOINT = "ibm-granite/granite-timeseries-ttm-r2"


class TtmOptions(StrictModel):
    predict_batch_size: int = Field(default=256, gt=0, description="Maximum prediction batch size.")


def _model_metadata() -> dict[str, Any]:
    import yaml

    text = (
        resources.files("tsfm_public.resources.model_paths_config")
        .joinpath("ttm.yaml")
        .read_text(encoding="utf-8")
    )
    return yaml.safe_load(text)["ibm-granite-models"]


@register_backbone(
    requires=["torch", "tsfm_public"],
    default_checkpoint=DEFAULT_CHECKPOINT,
    license="Apache-2.0",
    license_url="https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2/blob/d6a79570cac0f33d526601cd3a0fc7c80a8f9a2f/README.md",
)
class TtmBackbone(Backbone):
    name: ClassVar[str] = "ttm"
    Options: ClassVar[type[BaseModel]] = TtmOptions
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"zero_shot", "head"},
        embed=False,
        quantiles=False,
        multivariate="native",
        needs_fit_stats=True,
    )
    model: Any = None

    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None, *, reporter: Reporter) -> None:
        """Store inputs; load the model at the first forecast or fine-tune call."""
        super().load(cfg, fit_stats, reporter=reporter)
        self.model = None
        self._fitted = False
        self._reported_length: int | None = None

    def _load_model(self, length: int, horizon: int, channels: list[str]) -> None:
        from tsfm_public.models.tinytimemixer import TinyTimeMixerConfig
        from tsfm_public.toolkit import get_model

        if self.model is None:
            source = self.cfg.checkpoint or DEFAULT_CHECKPOINT
            branch = self.cfg.revision
            local = Path(source).expanduser()
            if branch is None and not local.is_dir() and not local.is_absolute():
                metadata = _model_metadata()
                available = sorted(
                    {
                        (v["context_length"], v["prediction_length"])
                        for v in metadata.values()
                        if v["model_card"] == source
                    }
                )
                try:
                    key = get_model(
                        model_path=source,
                        context_length=length,
                        prediction_length=horizon,
                        return_model_key=True,
                        force_return=None,
                    )
                    if not isinstance(key, str):
                        raise BackboneLoadError(
                            "TTM checkpoint selector did not return a model key"
                        )
                    branch = metadata[key]["revision"]
                except (ValueError, KeyError) as exc:
                    raise BackboneLoadError(
                        f"TTM does not support L={length}, H={horizon}; available L/H: {available}"
                    ) from exc
            checkpoint = resolve_checkpoint(
                self.cfg.model_copy(update={"checkpoint": source, "revision": branch})
            )
            self.resolved_checkpoint = checkpoint
            if self.cfg.revision is None:
                self.reporter.log(
                    f"checkpoint revision was not pinned; resolved revision: {checkpoint.revision}",
                    level="warning",
                )
            native = TinyTimeMixerConfig.from_pretrained(checkpoint.path, local_files_only=True)
            if horizon > native.prediction_length:
                raise BackboneLoadError(
                    f"TTM checkpoint supports H <= {native.prediction_length}; requested {horizon}"
                )
            self.model = get_model(
                model_path=str(checkpoint.path),
                context_length=length,
                prediction_length=native.prediction_length,
                model_revision=branch or "local",
                num_input_channels=len(channels),
                local_files_only=True,
                dtype=torch_dtype(self.cfg),
            )
            if self.model is None or isinstance(self.model, str):
                raise BackboneLoadError("TTM checkpoint factory did not return a model")
            self.model.to(device=self.cfg.device)
            self.channels = list(channels)
            self.context_length, self.horizon = length, horizon
            self.model.eval()

    def _ensure_model(self, length: int, horizon: int, channels: list[str]) -> None:
        with checkpoint_loading(self.name, self.cfg.checkpoint or DEFAULT_CHECKPOINT):
            self._load_model(length, horizon, channels)
        if channels != self.channels:
            raise ValueError("TTM channel order differs from the loaded model")
        if horizon > self.model.config.prediction_length:
            raise BackboneLoadError(
                f"TTM checkpoint supports H <= {self.model.config.prediction_length}"
            )
        native_length = self.model.config.masked_context_length or self.model.config.context_length
        if getattr(self, "_reported_length", None) != length:
            self.reporter.metric("requested_context_length", float(length))
            self.reporter.metric("effective_context_length", float(native_length))
            if length != native_length:
                self.reporter.log(
                    f"TTM requested context {length}; native context {native_length}",
                    level="warning",
                )
            self._reported_length = length

    def _frequency_token(self, freq: str, reporter: Reporter) -> int | None:
        if not self.model.config.resolution_prefix_tuning:
            return None
        from tsfm_public.toolkit.time_series_preprocessor import TimeSeriesPreprocessor

        processor = TimeSeriesPreprocessor()
        try:
            token = processor.get_frequency_token(freq)
        except ValueError:
            raise ValueError(f"invalid TTM frequency '{freq}'") from None
        if not 0 <= token < self.model.config.frequency_token_vocab_size:
            raise CapabilityError(f"TTM frequency token {token} exceeds the checkpoint vocabulary")
        if token == processor.frequency_mapping["oov"]:
            reporter.log(
                f"TTM frequency '{freq}' uses the library OOV token {token}", level="warning"
            )
        return token

    def _inputs(
        self,
        values: NDArray[np.float32],
        means: Any,
        scales: Any,
        freq_token: int | None,
    ) -> dict[str, Any]:
        import torch

        filled = ffill_bfill((values - means) / scales)
        inputs = {
            "past_values": torch.as_tensor(
                filled.transpose(0, 2, 1), device=self.cfg.device, dtype=torch_dtype(self.cfg)
            ),
            "past_observed_mask": torch.as_tensor(
                (~np.isnan(values)).transpose(0, 2, 1), device=self.cfg.device
            ),
        }
        if freq_token is not None:
            inputs["freq_token"] = torch.full(
                (len(values),), freq_token, device=self.cfg.device, dtype=torch.long
            )
        return inputs

    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput:
        import torch

        self._check_batch(batch, horizon)
        self._ensure_model(batch.values.shape[-1], horizon, batch.channel_names)
        freq_token = self._frequency_token(batch.freq, self.reporter)
        means, scales = fit_scaling(self.fit_stats, batch.channel_names, self.reporter)
        pieces = []
        self.model.eval()
        for start in range(0, len(batch.values), self.options.predict_batch_size):
            values = batch.values[start : start + self.options.predict_batch_size]
            with torch.no_grad(), autocast(self.cfg):
                output = self.model(
                    **self._inputs(values, means, scales, freq_token), return_loss=False
                )
            pieces.append(
                output.prediction_outputs[:, :horizon].float().cpu().numpy().transpose(0, 2, 1)
            )
        return ForecastOutput((np.concatenate(pieces) * scales + means).astype(np.float32))

    def finetune(
        self,
        train: SegmentSet,
        val: SegmentSet | None,
        cfg: FinetuneConfig,
        context_length: int,
        horizon: int,
        reporter: Reporter,
        *,
        mode: FinetuneMode,
    ) -> None:
        self._check_mode(mode)
        import torch

        if val is not None and val.freq != train.freq:
            raise ValueError("TTM training and validation frequency differs")
        self._ensure_model(context_length, horizon, train.channel_names)
        freq_token = self._frequency_token(train.freq, reporter)
        for name, parameter in self.model.named_parameters():
            parameter.requires_grad_(not name.startswith("backbone."))
        means, scales = fit_scaling(self.fit_stats, train.channel_names, reporter)

        def loss(x: NDArray[np.float32], y: NDArray[np.float32]) -> Any:
            self.model.backbone.eval()
            observed = ~np.isnan(y)
            if not observed.any():
                raise ValueError("TTM training batch has no observed targets")
            native_horizon = self.model.config.prediction_length
            normalized = np.nan_to_num((y - means) / scales, nan=0.0)
            target = np.zeros((len(y), y.shape[1], native_horizon), dtype=np.float32)
            mask = np.zeros_like(target, dtype=bool)
            target[..., :horizon], mask[..., :horizon] = normalized, observed
            return self.model(
                **self._inputs(x, means, scales, freq_token),
                future_values=torch.as_tensor(
                    target.transpose(0, 2, 1), device=self.cfg.device, dtype=torch_dtype(self.cfg)
                ),
                future_observed_mask=torch.as_tensor(
                    mask.transpose(0, 2, 1), device=self.cfg.device
                ),
            ).loss

        train_model(self.model, train, val, cfg, self.cfg, context_length, horizon, reporter, loss)
        self._fitted = True

    def save_adapter(self, path: Path) -> None:
        import torch

        if not self._fitted:
            raise CapabilityError("TTM has no fitted head adapter")
        path.mkdir(parents=True, exist_ok=True)
        state = {
            n: t.detach().cpu()
            for n, t in self.model.state_dict().items()
            if not n.startswith("backbone.")
        }
        torch.save(state, path / "head.pt")
        (path / "head.json").write_text(
            json.dumps(
                {
                    "context_length": self.context_length,
                    "horizon": self.horizon,
                    "channels": self.channels,
                    "resolved_revision": (
                        None
                        if self.resolved_checkpoint is None
                        else self.resolved_checkpoint.revision
                    ),
                }
            ),
            encoding="utf-8",
        )

    def load_adapter(self, path: Path) -> None:
        import torch

        with checkpoint_loading(self.name, path):
            saved = json.loads((path / "head.json").read_text(encoding="utf-8"))
        self._ensure_model(saved["context_length"], saved["horizon"], saved["channels"])
        if saved["resolved_revision"] is not None and (
            self.resolved_checkpoint is None
            or self.resolved_checkpoint.revision != saved["resolved_revision"]
        ):
            raise BackboneLoadError("TTM adapter checkpoint revision differs from the loaded model")
        with checkpoint_loading(self.name, path):
            state = torch.load(path / "head.pt", map_location=self.cfg.device, weights_only=True)
            result = self.model.load_state_dict(state, strict=False)
        if result.unexpected_keys or any(
            not k.startswith("backbone.") for k in result.missing_keys
        ):
            raise BackboneLoadError("TTM adapter weights do not match the checkpoint")
        self.model.eval()
        self._fitted = True
