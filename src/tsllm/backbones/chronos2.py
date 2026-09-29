"""Apache-2.0 Chronos-2 with native NaN masks and model-internal normalization."""

from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from typing import Any, ClassVar, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, field_validator

from tsllm.backbones.base import (
    Backbone,
    BackboneLoadError,
    Capabilities,
    CapabilityError,
    FinetuneMode,
    ForecastOutput,
)
from tsllm.backbones.checkpoint import checkpoint_loading
from tsllm.backbones.registry import register_backbone
from tsllm.backbones.training import report_parameters, torch_dtype
from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.config.base import StrictModel
from tsllm.data.stats import FitStats
from tsllm.data.types import ContextBatch, SegmentSet
from tsllm.reporting import Reporter

DEFAULT_CHECKPOINT = "amazon/chronos-2"
LORA_TARGET_MODULES = [
    "self_attention.q",
    "self_attention.v",
    "self_attention.k",
    "self_attention.o",
    "output_patch_embedding.output_layer",
]


class Chronos2Options(StrictModel):
    quantile_levels: list[float] | None = Field(
        default=None, description="Requested quantile levels."
    )
    embed_channel_pool: Literal["concat", "mean"] = Field(
        default="concat", description="Concatenate or average channel embeddings."
    )
    predict_batch_size: int = Field(default=256, gt=0, description="Maximum prediction batch size.")

    @field_validator("quantile_levels")
    @classmethod
    def valid_levels(cls, levels: list[float] | None) -> list[float] | None:
        if levels is not None and (
            not levels or sorted(set(levels)) != levels or any(not 0 < q < 1 for q in levels)
        ):
            raise ValueError(
                "quantile levels must be increasing unique values between zero and one"
            )
        return levels


@register_backbone(
    requires=["torch", "chronos"],
    default_checkpoint=DEFAULT_CHECKPOINT,
    license="Apache-2.0",
    license_url="https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/README.md",
)
class Chronos2Backbone(Backbone):
    name: ClassVar[str] = "chronos2"
    Options: ClassVar[type[BaseModel]] = Chronos2Options
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"zero_shot", "lora", "full"},
        embed=True,
        quantiles=True,
        multivariate="native",
    )
    pipeline: Any
    _fit_directory: TemporaryDirectory[str] | None = None
    _adapter_source: Path | None = None

    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None, *, reporter: Reporter) -> None:
        super().load(cfg, fit_stats, reporter=reporter)
        self._fit_directory = None
        self._adapter_source = None
        with checkpoint_loading(self.name, cfg.checkpoint or DEFAULT_CHECKPOINT):
            from chronos import Chronos2Pipeline

            checkpoint = self._resolve(DEFAULT_CHECKPOINT)
            self.pipeline = Chronos2Pipeline.from_pretrained(
                checkpoint.path,
                device_map=cfg.device,
                dtype=torch_dtype(cfg),
                local_files_only=True,
            )
            self.pipeline.model.eval()

    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput:
        import torch

        self._check_batch(batch, horizon)
        native = np.asarray(self.pipeline.model.chronos_config.quantiles)
        levels = self.options.quantile_levels or native.tolist()
        if min(levels) < native[0] or max(levels) > native[-1]:
            raise CapabilityError("requested quantiles are outside the Chronos checkpoint range")
        predictions = self.pipeline.predict(
            torch.as_tensor(batch.values),
            prediction_length=horizon,
            context_length=batch.values.shape[-1],
            batch_size=self.options.predict_batch_size,
            cross_learning=False,
        )
        quantiles = np.stack([p.float().cpu().numpy().transpose(0, 2, 1) for p in predictions])
        means = np.apply_along_axis(lambda row: np.interp(0.5, native, row), -1, quantiles)
        selected = np.apply_along_axis(lambda row: np.interp(levels, native, row), -1, quantiles)
        return ForecastOutput(means.astype(np.float32), selected.astype(np.float32), list(levels))

    def embed(self, batch: ContextBatch) -> NDArray[np.float32]:
        import torch

        self._check_batch(batch)
        embeddings, _ = self.pipeline.embed(
            torch.as_tensor(batch.values),
            context_length=batch.values.shape[-1],
            batch_size=self.options.predict_batch_size,
        )
        pooled = np.stack([value[:, :-1].mean(dim=1).float().cpu().numpy() for value in embeddings])
        return (
            pooled.mean(axis=1)
            if self.options.embed_channel_pool == "mean"
            else pooled.reshape(len(pooled), -1)
        ).astype(np.float32)

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
        if mode == "lora" and find_spec("peft") is None:
            raise BackboneLoadError(
                "Chronos LoRA requires peft; full fine-tuning is not a fallback"
            )
        if mode == "lora":
            try:
                import_module("peft")
            except ImportError as exc:
                raise BackboneLoadError("Chronos LoRA requires an importable peft") from exc
        from transformers import TrainerCallback

        if val is not None and val.channel_names != train.channel_names:
            raise ValueError("Chronos training and validation channel order differs")
        if not train.arrays or not any(
            a.shape[-1] >= context_length + horizon for a in train.arrays
        ):
            raise ValueError("no Chronos segment is long enough for a training window")

        class ReporterCallback(TrainerCallback):
            def on_train_begin(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
                trainable, total = report_parameters(kwargs["model"], reporter)
                if mode == "lora" and not 0 < trainable < total:
                    raise BackboneLoadError(
                        "Chronos LoRA did not create a partial trainable adapter"
                    )

            def on_log(
                self, args: Any, state: Any, control: Any, logs: Any = None, **kwargs: Any
            ) -> None:
                for name, output in [("loss", "train_loss"), ("eval_loss", "val_loss")]:
                    if logs is not None and name in logs:
                        reporter.metric(output, float(logs[name]), int(state.global_step))

            def on_step_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
                reporter.progress(int(state.global_step), cfg.num_steps)

        lora = (
            None
            if mode == "full"
            else {
                "r": cfg.lora.r,
                "lora_alpha": cfg.lora.alpha,
                "lora_dropout": cfg.lora.dropout,
                "target_modules": cfg.lora.target_modules or LORA_TARGET_MODULES,
            }
        )
        self._fit_directory = TemporaryDirectory(prefix="tsllm-chronos-")
        directory = Path(self._fit_directory.name)
        validation = (
            {} if val is None else {"eval_steps": cfg.eval_every, "save_steps": cfg.eval_every}
        )
        self.pipeline = self.pipeline.fit(
            inputs=train.arrays,
            validation_inputs=None if val is None else val.arrays,
            prediction_length=horizon,
            context_length=context_length,
            min_past=context_length,
            finetune_mode=mode,
            lora_config=lora,
            learning_rate=cfg.learning_rate,
            num_steps=cfg.num_steps,
            batch_size=cfg.batch_size,
            output_dir=directory,
            callbacks=[ReporterCallback()],
            remove_printer_callback=True,
            dataloader_num_workers=0,
            max_grad_norm=cfg.grad_clip,
            logging_steps=1,
            disable_tqdm=True,
            bf16=self.cfg.device == "cuda" and self.cfg.dtype == "bf16",
            tf32=False,
            **validation,
        )
        self.pipeline.model.to(dtype=torch_dtype(self.cfg)).eval()
        self._adapter_source = directory / "finetuned-ckpt"
        self.pipeline.save_pretrained(self._adapter_source)

    def save_adapter(self, path: Path) -> None:
        if self._adapter_source is None:
            raise CapabilityError("Chronos has no fitted adapter")
        if path.resolve() != self._adapter_source.resolve():
            copytree(self._adapter_source, path, dirs_exist_ok=True)

    def load_adapter(self, path: Path) -> None:
        with checkpoint_loading(self.name, path):
            from chronos import Chronos2Pipeline

            self.pipeline = Chronos2Pipeline.from_pretrained(
                path, device_map=self.cfg.device, dtype=torch_dtype(self.cfg), local_files_only=True
            )
            self.pipeline.model.eval()
            self._adapter_source = path
