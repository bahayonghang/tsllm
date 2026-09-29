"""Read source tables with explicit numeric and timestamp types."""

import polars as pl

from tsllm.config.dataset import RESERVED_COLUMNS, DatasetConfig
from tsllm.data.registry import DatasetConfigError


def read_source(cfg: DatasetConfig) -> pl.DataFrame:
    try:
        return _read_source(cfg)
    except (pl.exceptions.PolarsError, OSError, UnicodeError):
        # Suppress the original chain: parser diagnostics can contain private values.
        raise DatasetConfigError(f"dataset '{cfg.id}' source cannot be parsed") from None


def _read_source(cfg: DatasetConfig) -> pl.DataFrame:
    selected = (
        None if cfg.channels is None else [c.name for c in cfg.channels if c.role != "ignore"]
    )
    if cfg.source.format == "csv":
        frame = pl.read_csv(
            cfg.source.path,
            columns=None if selected is None else [cfg.source.time_column, *selected],
            schema_overrides={cfg.source.time_column: pl.String}
            | dict.fromkeys(selected or [], pl.Float64),
            infer_schema=selected is not None,
            try_parse_dates=False,
            encoding=cfg.source.encoding,
        )
    else:
        frame = pl.read_parquet(cfg.source.path)
    time_col = cfg.source.time_column
    if frame.is_empty() or time_col not in frame.columns:
        raise DatasetConfigError(f"dataset '{cfg.id}' requires source rows and a timestamp column")
    if selected is None:
        selected = []
        for name, dtype in frame.schema.items():
            if name == time_col:
                continue
            column = frame[name]
            if cfg.source.format == "csv":
                numeric = column.cast(pl.Float64, strict=False)
                include = numeric.null_count() == column.null_count()
            else:
                include = dtype.is_numeric() or column.null_count() == frame.height
            if include:
                selected.append(name)
    if not selected:
        raise DatasetConfigError(f"dataset '{cfg.id}' has no numeric channels")
    if set(selected) & RESERVED_COLUMNS:
        raise DatasetConfigError(f"dataset '{cfg.id}' has reserved channel names")
    if any(name not in frame.columns for name in selected):
        raise DatasetConfigError(f"dataset '{cfg.id}' has a missing configured channel")
    time_dtype = frame.schema[time_col]
    if time_dtype == pl.String:
        time_expr = pl.col(time_col).str.to_datetime(format=cfg.source.time_format, time_unit="us")
    elif time_dtype == pl.Date or isinstance(time_dtype, pl.Datetime):
        time_expr = pl.col(time_col).cast(pl.Datetime("us"))
        if isinstance(time_dtype, pl.Datetime) and time_dtype.time_zone is not None:
            raise DatasetConfigError(f"dataset '{cfg.id}' timestamps must have no timezone")
    else:
        raise DatasetConfigError(f"dataset '{cfg.id}' timestamp type is invalid")
    frame = frame.select(
        time_expr.alias("time"),
        *[pl.col(name).cast(pl.Float64, strict=True).fill_nan(None) for name in selected],
    )
    parsed_dtype = frame.schema["time"]
    if isinstance(parsed_dtype, pl.Datetime) and parsed_dtype.time_zone is not None:
        raise DatasetConfigError(f"dataset '{cfg.id}' timestamps must have no timezone")
    if frame["time"].null_count():
        raise DatasetConfigError(f"dataset '{cfg.id}' has missing timestamps")
    if frame.select(pl.any_horizontal(pl.col(selected).is_infinite()).any()).item():
        raise DatasetConfigError(f"dataset '{cfg.id}' contains non-finite channel values")
    keep = "first" if cfg.dedup == "keep_first" else "last"
    return frame.unique(subset="time", keep=keep, maintain_order=True).sort("time")
