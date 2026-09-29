"""Future-event label rules shared with run configuration."""

from typing import Literal, Self

from pydantic import Field, model_validator

from tsllm.config.base import StrictModel


class ThresholdSpec(StrictModel):
    quantile: float | None = Field(default=None, ge=0, le=1, description="Eligible fit quantile.")
    value: float | None = Field(default=None, allow_inf_nan=False, description="Fixed threshold.")

    @model_validator(mode="after")
    def one_source(self) -> Self:
        if (self.quantile is None) == (self.value is None):
            raise ValueError("exactly one threshold source is required")
        return self


class OutsideThreshold(StrictModel):
    low: ThresholdSpec | float = Field(description="Lower fixed threshold or fit quantile.")
    high: ThresholdSpec | float = Field(description="Upper fixed threshold or fit quantile.")


class FutureEventRule(StrictModel):
    type: Literal["future_event"] = Field(default="future_event", description="Label rule type.")
    channel: str = Field(min_length=1, description="Event channel.")
    op: Literal["gt", "lt", "outside"] = Field(description="Event comparison.")
    threshold: ThresholdSpec | OutsideThreshold = Field(description="Threshold definition.")
    window: int = Field(gt=0, description="Future window length in grid steps.")
    min_duration: int = Field(gt=0, description="Consecutive event steps required.")

    @model_validator(mode="after")
    def compatible_threshold(self) -> Self:
        if (self.op == "outside") != isinstance(self.threshold, OutsideThreshold):
            raise ValueError("outside requires low and high thresholds; gt and lt require one")
        if self.min_duration > self.window:
            raise ValueError("minimum event duration exceeds label window")
        return self
