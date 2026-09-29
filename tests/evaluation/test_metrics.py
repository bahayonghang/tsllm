import math

import numpy as np
import pytest
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

from tsllm.evaluation.metrics import choose_threshold, classification_metrics, forecast_metrics
from tsllm.evaluation.resources import latency_percentiles


def _arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = np.array([[[1, 2], [0, 0]], [[3, 4], [0, 0]]], dtype=np.float32)  # (N=2, C=2, H=2)
    pred = np.array([[[2, 2], [1, 1]], [[3, 6], [1, 1]]], dtype=np.float32)
    mask = np.ones_like(y, dtype=bool)
    mask[1, 1, 1] = False
    return y, pred, mask


def test_forecast_metrics_hand_example() -> None:
    y, pred, mask = _arrays()
    levels = [0.1, 0.5, 0.9]
    quantiles = np.stack([pred - 1, pred, pred + 1], axis=-1)
    result = forecast_metrics(y, mask, pred, quantiles, levels, [0.5, 2.0], [1, 2], ["a", "b"])

    # Channel a errors: 1, 0, 0, 2. Channel b errors: 1, 1, 1 (one target masked).
    assert result["per_channel"]["a"] == pytest.approx(
        {"mae": 0.75, "rmse": math.sqrt(1.25), "n": 4}
    )
    assert result["per_channel"]["b"] == pytest.approx({"mae": 1.0, "rmse": 1.0, "n": 3})
    overall = result["overall"]
    assert overall["mae_norm_macro"] == pytest.approx((0.75 / 0.5 + 1 / 2) / 2)
    assert overall["rmse_norm_macro"] == pytest.approx((math.sqrt(1.25) / 0.5 + 1 / 2) / 2)
    assert result["per_lead"]["1"]["mae_norm_macro"] == pytest.approx((0.5 / 0.5 + 1 / 2) / 2)
    assert result["per_lead"]["2"]["mae_norm_macro"] == pytest.approx((1 / 0.5 + 1 / 2) / 2)
    # |error| <= 1 at 6 of 7 observed targets; the interval width is 2 everywhere.
    assert overall["coverage_80"] == pytest.approx(6 / 7)
    assert overall["width_80"] == pytest.approx((2 / 0.5 + 2 / 2) / 2)

    expected = []
    for k, level in enumerate(levels):
        for c, std in enumerate([0.5, 2.0]):
            losses = [
                max(level * d, (level - 1) * d)
                for d in (y[..., c, :] - quantiles[..., c, :, k])[mask[:, c, :]]
            ]
            expected.append(np.mean(losses) / std)
    assert overall["pinball"] == pytest.approx(np.mean(expected))
    assert result["excluded_channels"] == [] and result["n_missing_predictions"] == 0


def test_forecast_metrics_zero_std_missing_quantiles_and_nan_predictions() -> None:
    y, pred, mask = _arrays()
    pred[0, 0, 0] = np.nan
    result = forecast_metrics(y, mask, pred, None, None, [0.5, 0.0], [], ["a", "b"])
    assert result["excluded_channels"] == ["b"]
    # Channel a keeps errors 0, 0, 2 after the NaN prediction is removed.
    assert result["overall"]["mae_norm_macro"] == pytest.approx((2 / 3) / 0.5)
    assert result["n_missing_predictions"] == 1
    assert result["overall"]["pinball"] is None and result["overall"]["coverage_80"] is None

    median_only = pred[..., None]
    partial = forecast_metrics(y, mask, pred, median_only, [0.5], [0.5, 1.0], [], ["a", "b"])
    assert partial["overall"]["pinball"] is not None
    assert partial["overall"]["coverage_80"] is None and partial["overall"]["width_80"] is None


def test_classification_metrics_match_sklearn() -> None:
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 2, 200).astype(np.int8)
    scores = np.clip(labels * 0.3 + rng.random(200) * 0.7, 0, 1)
    threshold = choose_threshold(labels, scores)
    assert threshold is not None
    best = max(f1_score(labels, (scores >= t).astype(int)) for t in np.unique(scores))
    assert f1_score(labels, (scores >= threshold).astype(int)) == pytest.approx(best)

    overall, curves, warnings = classification_metrics(labels, scores, threshold)
    predicted = (scores >= threshold).astype(int)
    assert overall["auroc"] == pytest.approx(roc_auc_score(labels, scores))
    assert overall["auprc"] == pytest.approx(average_precision_score(labels, scores))
    assert overall["brier"] == pytest.approx(brier_score_loss(labels, scores))
    assert overall["f1"] == pytest.approx(f1_score(labels, predicted))
    assert overall["confusion"] == confusion_matrix(labels, predicted).tolist()
    assert overall["positive_rate"] == pytest.approx(labels.mean())
    assert 0 < len(curves["roc"]) <= 200 and 0 < len(curves["pr"]) <= 200
    assert warnings == []


def test_single_class_split() -> None:
    labels = np.zeros(10, dtype=np.int8)
    scores = np.linspace(0, 1, 10)
    assert choose_threshold(labels, scores) is None
    overall, curves, warnings = classification_metrics(labels, scores, 0.5)
    assert overall["auroc"] is None and overall["auprc"] is None
    assert overall["f1"] == 0.0 and curves == {"roc": [], "pr": []}
    assert len(warnings) == 1


def test_latency_percentiles() -> None:
    assert latency_percentiles([]) == (None, None)
    p50, p95 = latency_percentiles([float(v) for v in range(1, 101)])
    assert p50 == pytest.approx(50.5) and p95 == pytest.approx(95.05)
