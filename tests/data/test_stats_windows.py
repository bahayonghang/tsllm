import ast
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import tsllm.data
from tsllm.config.dataset import SPLIT_NAMES, SplitName
from tsllm.data.registry import DatasetConfigError
from tsllm.data.stats import compute_fit_stats
from tsllm.data.types import PreparedFrame
from tsllm.data.windows import (
    build_eval_manifest,
    build_train_manifest,
    context_batch,
    origin_set_hash,
    segment_set,
    targets,
)


@pytest.mark.parametrize("split", ["val", "cal", "test"])
def test_fit_statistics_ignore_future(prepared_frame: PreparedFrame, split: str) -> None:
    baseline = compute_fit_stats(prepared_frame)
    changed = prepared_frame.frame.with_columns(
        [
            pl.when(pl.col("split") == split)
            .then(1e12)
            .otherwise(pl.col(c))
            .cast(pl.Float32)
            .alias(c)
            for c in prepared_frame.channels
        ]
    )
    assert compute_fit_stats(replace(prepared_frame, frame=changed)) == baseline


def test_stats_ignore_ineligible_fit_rows(prepared_frame: PreparedFrame) -> None:
    baseline = compute_fit_stats(prepared_frame)
    changed = prepared_frame.frame.with_columns(
        pl.when(~pl.col("eligible")).then(1e12).otherwise(pl.col("x")).alias("x")
    )
    assert compute_fit_stats(replace(prepared_frame, frame=changed)) == baseline
    expected = np.array([i for i in range(60) if i not in [10, 15]])
    channel = baseline.channels["x"]
    assert channel.count == 58
    assert channel.mean == pytest.approx(expected.mean())
    assert channel.std == pytest.approx(expected.std(ddof=1))
    for quantile, value in channel.quantiles.items():
        assert value == pytest.approx(np.quantile(expected, float(quantile)))


def test_empty_and_constant_channel_stats(prepared_frame: PreparedFrame) -> None:
    frame = prepared_frame.frame.with_columns(
        pl.lit(None, dtype=pl.Float32).alias("x"), pl.lit(2.0).alias("y")
    )
    result = compute_fit_stats(replace(prepared_frame, frame=frame))
    assert result.channels["x"].count == 0
    assert result.channels["x"].mean is None
    assert result.channels["x"].std is None
    assert all(value is None for value in result.channels["x"].quantiles.values())
    assert result.channels["y"].std == 0
    with pytest.raises(DatasetConfigError):
        compute_fit_stats(
            replace(prepared_frame, frame=frame.with_columns(pl.lit(False).alias("eligible")))
        )


def reference_origins(prepared: PreparedFrame, split: str, length: int, horizon: int) -> list[int]:
    segments = prepared.frame["segment_id"].to_list()
    splits = prepared.frame["split"].to_list()
    return [
        o
        for o in range(length - 1, prepared.frame.height - horizon)
        if len(set(segments[o - length + 1 : o + horizon + 1])) == 1
        and segments[o] >= 0
        and set(splits[o + 1 : o + horizon + 1]) == {split}
    ]


def test_train_targets_stay_fit_and_windows_stay_in_one_segment(
    prepared_frame: PreparedFrame,
) -> None:
    manifest = build_train_manifest(prepared_frame, 6, 5)
    origins = manifest["origin_row"].to_list()
    assert origins and origins == reference_origins(prepared_frame, "fit", 6, 5)
    for origin in origins:
        window = prepared_frame.frame.slice(origin - 5, 11)
        assert window["segment_id"].n_unique() == 1
        assert window["segment_id"][0] >= 0
        assert prepared_frame.frame.slice(origin + 1, 5)["split"].to_list() == ["fit"] * 5
    assert 27 not in origins
    assert 57 not in origins


@pytest.mark.parametrize("split", ["val", "cal", "test"])
def test_eval_targets_stay_in_split(prepared_frame: PreparedFrame, split: SplitName) -> None:
    manifest = build_eval_manifest(prepared_frame, split, 6, 5)
    assert manifest["origin_row"].to_list() == reference_origins(prepared_frame, split, 6, 5)
    assert manifest.height > 0
    for origin in manifest["origin_row"].to_list():
        assert prepared_frame.frame.slice(origin + 1, 5)["split"].to_list() == [split] * 5


def test_eval_context_may_use_fit_history(prepared_frame: PreparedFrame) -> None:
    manifest = build_eval_manifest(prepared_frame, "val", 6, 5)
    assert manifest["origin_row"][0] == 59
    batch = context_batch(prepared_frame, [59], 6)
    np.testing.assert_allclose(batch.values[0, 0], np.arange(54, 60), rtol=1e-6)


def test_deterministic_stride_and_even_limit(prepared_frame: PreparedFrame) -> None:
    train = build_train_manifest(prepared_frame, 3, 2, stride=3)
    assert train["origin_row"].to_list() == [
        o for o in reference_origins(prepared_frame, "fit", 3, 2) if o % 3 == 0
    ]
    expected = [o for o in reference_origins(prepared_frame, "test", 3, 2) if o % 2 == 0]
    chosen = [expected[i] for i in np.linspace(0, len(expected) - 1, 3).astype(int)]
    first = build_eval_manifest(prepared_frame, "test", 3, 2, stride=2, max_eval_origins=3)
    second = build_eval_manifest(prepared_frame, "test", 3, 2, stride=2, max_eval_origins=3)
    assert first["origin_row"].to_list() == chosen
    assert origin_set_hash(first) == origin_set_hash(second)
    assert origin_set_hash(first) != origin_set_hash(first.head(2))


def test_batch_shapes_order_missing_and_units(prepared_frame: PreparedFrame) -> None:
    batch = context_batch(prepared_frame, [16, 69], 3)
    assert batch.values.shape == (2, 2, 3)
    assert batch.values.dtype == np.float32
    assert batch.origin_time.dtype == np.dtype("datetime64[us]")
    assert batch.freq == "1min" and batch.channel_names == ["x", "y"]
    assert np.isnan(batch.values[0, 0, 1])
    np.testing.assert_allclose(batch.values[0, 1], [28, 30, 32], rtol=1e-6)
    values, mask = targets(prepared_frame, [69], 3)
    assert values.shape == mask.shape == (1, 2, 3)
    assert values.dtype == np.float32 and mask.dtype == np.bool_
    assert np.isnan(values[0, 0, 0]) and not mask[0, 0, 0]
    np.testing.assert_allclose(values[0, 1], [140, 142, 144], rtol=1e-6)


def test_empty_manifest_and_batches(prepared_frame: PreparedFrame) -> None:
    manifest = build_train_manifest(prepared_frame, 1000, 5)
    assert manifest.is_empty()
    assert manifest.schema["origin_time"] == pl.Datetime("us")
    assert context_batch(prepared_frame, [], 4).values.shape == (0, 2, 4)
    assert targets(prepared_frame, [], 3)[0].shape == (0, 2, 3)


def test_invalid_extraction_rejected(prepared_frame: PreparedFrame) -> None:
    with pytest.raises(ValueError, match="segment"):
        context_batch(prepared_frame, [33], 5)
    with pytest.raises(ValueError, match="bounds"):
        context_batch(prepared_frame, [1], 5)
    with pytest.raises(ValueError, match="split"):
        targets(prepared_frame, [58], 5)
    with pytest.raises(ValueError, match="segment"):
        targets(prepared_frame, [28], 5)


def test_segment_set_truncates_fit_boundary(prepared_frame: PreparedFrame) -> None:
    result = segment_set(prepared_frame, "fit", min_rows=28)
    assert len(result.arrays) == 1
    assert result.arrays[0].shape == (2, 30)
    assert np.isnan(result.arrays[0][0, 15])
    result = segment_set(prepared_frame, "fit", min_rows=20)
    assert [a.shape for a in result.arrays] == [(2, 30), (2, 27)]
    assert result.arrays[-1][0, -1] == 59
    assert result.freq == "1min"
    for split in SPLIT_NAMES:
        selected = segment_set(prepared_frame, split)
        assert all(a.dtype == np.float32 for a in selected.arrays)


def test_data_layer_has_no_model_imports() -> None:
    forbidden = {"torch", "transformers", "chronos", "tsfm_public", "peft"}
    root = Path(tsllm.data.__file__).parent
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert forbidden.isdisjoint(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden


def test_data_import_in_independent_process(tmp_path: Path) -> None:
    code = (
        "import sys; import tsllm.data; "
        "assert not {'torch', 'transformers', 'chronos', 'tsfm_public', 'peft'} & set(sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
