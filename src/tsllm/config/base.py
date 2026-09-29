"""Common configuration types."""

import re
from datetime import timedelta
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer, WithJsonSchema


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


def parse_duration(value: object) -> timedelta:
    if isinstance(value, timedelta):
        result = value
    elif isinstance(value, str):
        match = re.fullmatch(r"([0-9]+(?:[.][0-9]+)?)(us|ms|s|min|h|d)", value)
        if match is None:
            raise ValueError("duration requires a number and a unit: us, ms, s, min, h, d")
        scale = {"us": 0.000001, "ms": 0.001, "s": 1, "min": 60, "h": 3600, "d": 86400}
        result = timedelta(seconds=float(match[1]) * scale[match[2]])
    else:
        raise ValueError("duration must be a unit string")
    if result <= timedelta(0):
        raise ValueError("duration must be positive")
    return result


def duration_string(value: timedelta) -> str:
    micros = value // timedelta(microseconds=1)
    for unit, scale in [
        ("d", 86400000000),
        ("h", 3600000000),
        ("min", 60000000),
        ("s", 1000000),
        ("ms", 1000),
        ("us", 1),
    ]:
        if micros % scale == 0:
            return f"{micros // scale}{unit}"
    raise ValueError("duration cannot be serialized")


Duration = Annotated[
    timedelta,
    BeforeValidator(parse_duration),
    PlainSerializer(duration_string, return_type=str),
    WithJsonSchema({"type": "string", "pattern": r"^[0-9]+(?:[.][0-9]+)?(us|ms|s|min|h|d)$"}),
]
