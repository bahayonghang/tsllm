"""Run, task, and job configuration."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from tsllm.config.backbone import BackboneConfig, FinetuneConfig
from tsllm.config.base import StrictModel
from tsllm.config.dataset import DatasetConfig
from tsllm.config.labels import FutureEventRule

EvalSplit = Literal["val", "cal", "test"]
RunMode = Literal["zero_shot", "lora", "head", "full"]

LabelRuleConfig = FutureEventRule


def _default_eval_splits() -> list[EvalSplit]:
    return ["val", "test"]


class ForecastTaskConfig(StrictModel):
    type: Literal["forecast"] = Field(default="forecast", description="Task type.")
    context_length: int = Field(gt=0, description="Context length in grid steps.")
    horizon: int = Field(gt=0, description="Forecast horizon in grid steps.")
    eval_leads: list[int] = Field(
        default_factory=list, description="Lead steps (1-based) that get separate metrics."
    )
    eval_splits: list[EvalSplit] = Field(
        default_factory=_default_eval_splits, min_length=1, description="Evaluated splits."
    )
    train_origin_stride: int = Field(
        default=1,
        gt=0,
        description="Training origin stride. Adapters sample forecast training windows from "
        "fit segments, so forecast runs do not use this value.",
    )
    eval_origin_stride: int = Field(default=1, gt=0, description="Evaluation origin stride.")
    max_eval_origins: int | None = Field(
        default=None, gt=0, description="Evenly spaced evaluation origin limit; null is no limit."
    )
    eval_batch_size: int = Field(default=64, gt=0, description="Forecast batch size.")

    @model_validator(mode="after")
    def valid_leads(self) -> Self:
        if any(lead < 1 or lead > self.horizon for lead in self.eval_leads):
            raise ValueError("evaluation leads must be between 1 and the horizon")
        if len(set(self.eval_splits)) != len(self.eval_splits):
            raise ValueError("evaluation splits must be unique")
        return self


class HeadConfig(StrictModel):
    type: Literal["logistic", "mlp"] = Field(default="logistic", description="Classifier head.")
    class_weight: Literal["balanced"] | None = Field(
        default="balanced", description="Class weighting; null gives equal sample weights."
    )
    C: float = Field(default=1.0, gt=0, description="Inverse regularization for logistic heads.")
    hidden_layer_sizes: list[int] = Field(
        default_factory=lambda: [64], min_length=1, description="Hidden layer sizes for MLP heads."
    )
    max_iter: int = Field(default=1000, gt=0, description="Maximum solver iterations.")


class ClassifyTaskConfig(StrictModel):
    type: Literal["classify"] = Field(default="classify", description="Task type.")
    context_length: int = Field(gt=0, description="Context length in grid steps.")
    eval_splits: list[EvalSplit] = Field(
        default_factory=_default_eval_splits, min_length=1, description="Evaluated splits."
    )
    train_origin_stride: int = Field(default=1, gt=0, description="Training origin stride.")
    eval_origin_stride: int = Field(default=1, gt=0, description="Evaluation origin stride.")
    max_train_origins: int = Field(
        default=20000, gt=0, description="Evenly spaced training origin limit."
    )
    max_eval_origins: int | None = Field(
        default=None, gt=0, description="Evenly spaced evaluation origin limit; null is no limit."
    )
    label: LabelRuleConfig = Field(description="Future event label rule.")
    head: HeadConfig = Field(default_factory=HeadConfig, description="Classifier head.")
    embed_batch_size: int = Field(default=64, gt=0, description="Representation batch size.")

    @model_validator(mode="after")
    def unique_splits(self) -> Self:
        if len(set(self.eval_splits)) != len(self.eval_splits):
            raise ValueError("evaluation splits must be unique")
        return self


TaskConfig = Annotated[ForecastTaskConfig | ClassifyTaskConfig, Field(discriminator="type")]


class RunConfig(StrictModel):
    name: str = Field(min_length=1, description="Run name.")
    dataset: str = Field(min_length=1, description="Dataset id.")
    task: TaskConfig = Field(description="Task configuration.")
    backbone: BackboneConfig = Field(description="Backbone configuration.")
    mode: RunMode = Field(description="Training mode; classification requires head.")
    finetune: FinetuneConfig = Field(
        default_factory=FinetuneConfig, description="Fine-tuning settings; zero_shot ignores them."
    )
    seed: int = Field(default=0, ge=0, description="Random seed.")
    notes: str = Field(default="", description="Free-text notes.")

    @model_validator(mode="after")
    def classify_uses_head(self) -> Self:
        if self.task.type == "classify" and self.mode != "head":
            raise ValueError("classification runs require mode 'head'")
        return self


class JobSpec(StrictModel):
    kind: Literal["experiment", "ingest"] = Field(description="Job kind.")
    dataset: DatasetConfig = Field(description="Dataset configuration snapshot.")
    run: RunConfig | None = Field(default=None, description="Run configuration; null for ingest.")

    @model_validator(mode="after")
    def run_matches_kind(self) -> Self:
        if self.kind == "ingest" and self.run is not None:
            raise ValueError("ingest jobs have no run configuration")
        if self.kind == "experiment":
            if self.run is None:
                raise ValueError("experiment jobs require a run configuration")
            if self.run.dataset != self.dataset.id:
                raise ValueError("run dataset does not match the dataset snapshot")
        return self
