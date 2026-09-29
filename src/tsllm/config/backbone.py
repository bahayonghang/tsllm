"""Shared backbone and fine-tuning configuration."""

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from tsllm.config.base import StrictModel


class LoraSpec(StrictModel):
    r: int = Field(default=8, gt=0, description="Low-rank adapter rank.")
    alpha: int = Field(default=16, gt=0, description="Low-rank adapter scaling factor.")
    dropout: float = Field(default=0.05, ge=0, lt=1, description="Adapter dropout rate.")
    target_modules: list[str] | None = Field(
        default=None, description="Module names; null selects the adapter defaults."
    )


class FinetuneConfig(StrictModel):
    learning_rate: float = Field(default=1e-5, gt=0, description="Optimizer learning rate.")
    num_steps: int = Field(default=1000, gt=0, description="Number of optimizer steps.")
    batch_size: int = Field(default=64, gt=0, description="Training batch size.")
    eval_every: int = Field(default=100, gt=0, description="Validation interval in steps.")
    grad_clip: float = Field(default=1.0, gt=0, description="Maximum gradient norm.")
    lora: LoraSpec = Field(default_factory=LoraSpec, description="Low-rank adapter settings.")


class BackboneConfig(StrictModel):
    name: str = Field(min_length=1, description="Backbone registry name.")
    checkpoint: str | None = Field(
        default=None, description="Hugging Face repository or local checkpoint directory."
    )
    revision: str | None = Field(default=None, description="Checkpoint revision to resolve.")
    device: Literal["cuda", "cpu"] = Field(default="cuda", description="Execution device.")
    dtype: Literal["fp32", "bf16"] = Field(default="bf16", description="CUDA numeric type.")
    options: dict[str, Any] = Field(default_factory=dict, description="Adapter-specific options.")

    @model_validator(mode="after")
    def cpu_uses_fp32(self) -> Self:
        if self.device == "cpu":
            self.dtype = "fp32"
        return self
