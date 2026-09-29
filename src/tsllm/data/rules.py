"""Compile eligibility rules to null-safe expressions."""

from typing import assert_never

import polars as pl

from tsllm.config.dataset import Condition, ConditionGroup
from tsllm.data.registry import DatasetConfigError


def _expression(rule: Condition | ConditionGroup, columns: list[str]) -> pl.Expr:
    if isinstance(rule, Condition):
        if rule.channel not in columns:
            raise DatasetConfigError(f"eligibility channel '{rule.channel}' is not selected")
        column = pl.col(rule.channel)
        match rule.op:
            case "gt":
                result = column > rule.value
            case "ge":
                result = column >= rule.value
            case "lt":
                result = column < rule.value
            case "le":
                result = column <= rule.value
            case "eq":
                result = column == rule.value
            case "ne":
                result = column != rule.value
            case _:
                assert_never(rule.op)
        return result.fill_null(False)
    children = rule.all if rule.all is not None else rule.any
    assert children is not None
    expressions = [_expression(child, columns) for child in children]
    return (
        pl.all_horizontal(expressions) if rule.all is not None else pl.any_horizontal(expressions)
    )


def evaluate(group: ConditionGroup | None, frame: pl.DataFrame, channels: list[str]) -> pl.Series:
    if group is None:
        expression = pl.any_horizontal(pl.col(channels).is_not_null())
    else:
        expression = _expression(group, channels)
    return frame.select(expression.alias("eligible"))["eligible"]
