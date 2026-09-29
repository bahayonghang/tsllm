"""Forecast and classification metrics.

Forecast errors are in physical units per channel. Cross-channel aggregates divide each
channel by its fit-split standard deviation first.
"""

from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

MAX_CURVE_POINTS = 200


def _mean(values: NDArray[np.float64]) -> float | None:
    finite = values[np.isfinite(values)]
    return float(finite.mean()) if finite.size else None


def _masked_mean(values: NDArray[np.float64], valid: NDArray[np.bool_]) -> NDArray[np.float64]:
    """Mean over axes 0 and 2 where valid is true; NaN for a channel without valid points."""
    counts = valid.sum(axis=(0, 2))
    total = np.where(valid, values, 0.0).sum(axis=(0, 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        return total / counts


def _channel_errors(
    err: NDArray[np.float64], valid: NDArray[np.bool_]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    return _masked_mean(np.abs(err), valid), np.sqrt(_masked_mean(err**2, valid))


def forecast_metrics(
    y_true: NDArray[np.floating],
    mask: NDArray[np.bool_],
    mean: NDArray[np.floating],
    quantiles: NDArray[np.floating] | None,
    quantile_levels: Sequence[float] | None,
    fit_std: Sequence[float | None],
    leads: Sequence[int],
    channel_names: Sequence[str],
) -> dict[str, Any]:
    """Metrics for arrays (N, C, H); quantiles are (N, C, H, Q)."""
    y = y_true.astype(np.float64)
    pred = mean.astype(np.float64)
    valid = mask & np.isfinite(pred) & np.isfinite(y)
    err = np.where(valid, pred - y, 0.0)
    std = np.array([np.nan if s is None else s for s in fit_std], dtype=np.float64)
    usable = np.isfinite(std) & (std > 0)
    scale = np.where(usable, std, np.nan)
    excluded = [name for name, ok in zip(channel_names, usable, strict=True) if not ok]

    mae_c, rmse_c = _channel_errors(err, valid)
    counts = valid.sum(axis=(0, 2))
    per_channel = {
        name: {"mae": _float(mae_c[c]), "rmse": _float(rmse_c[c]), "n": int(counts[c])}
        for c, name in enumerate(channel_names)
    }
    overall: dict[str, float | None] = {
        "mae_norm_macro": _mean(mae_c / scale),
        "rmse_norm_macro": _mean(rmse_c / scale),
        "pinball": None,
        "coverage_80": None,
        "width_80": None,
    }

    per_lead = {}
    for lead in leads:
        step = slice(lead - 1, lead)
        lead_mae, lead_rmse = _channel_errors(err[:, :, step], valid[:, :, step])
        per_lead[str(lead)] = {
            "mae_norm_macro": _mean(lead_mae / scale),
            "rmse_norm_macro": _mean(lead_rmse / scale),
        }

    if quantiles is not None and quantile_levels is not None:
        q = quantiles.astype(np.float64)
        levels = np.asarray(quantile_levels, dtype=np.float64)
        per_q = []
        for k, level in enumerate(levels):
            q_valid = valid & np.isfinite(q[..., k])
            diff = np.where(q_valid, y - q[..., k], 0.0)
            loss = np.maximum(level * diff, (level - 1) * diff)
            per_q.append(_masked_mean(loss, q_valid) / scale)
        overall["pinball"] = _mean(np.stack(per_q))
        low = np.flatnonzero(np.isclose(levels, 0.1))
        high = np.flatnonzero(np.isclose(levels, 0.9))
        if low.size and high.size:
            lo, hi = q[..., low[0]], q[..., high[0]]
            both = valid & np.isfinite(lo) & np.isfinite(hi)
            if both.any():
                overall["coverage_80"] = float(((lo <= y) & (y <= hi))[both].mean())
                overall["width_80"] = _mean(_masked_mean(hi - lo, both) / scale)

    return {
        "overall": overall,
        "per_channel": per_channel,
        "per_lead": per_lead,
        "excluded_channels": excluded,
        "n_missing_predictions": int((mask & ~np.isfinite(pred)).sum()),
    }


def _float(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _downsample(points: NDArray[np.float64]) -> list[list[float]]:
    if len(points) > MAX_CURVE_POINTS:
        points = points[np.linspace(0, len(points) - 1, MAX_CURVE_POINTS).astype(np.int64)]
    return points.tolist()


def choose_threshold(labels: NDArray[np.integer], scores: NDArray[np.floating]) -> float | None:
    """Decision threshold with the largest F1 on the given split; None for one class."""
    from sklearn.metrics import precision_recall_curve

    if np.unique(labels).size < 2:
        return None
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    with np.errstate(invalid="ignore", divide="ignore"):
        f1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1])
    return float(thresholds[int(np.nanargmax(f1))])


def classification_metrics(
    labels: NDArray[np.integer], scores: NDArray[np.floating], threshold: float
) -> tuple[dict[str, Any], dict[str, list[list[float]]], list[str]]:
    """Return overall metrics, ROC/PR curves, and warnings for one split."""
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        confusion_matrix,
        precision_recall_curve,
        roc_auc_score,
        roc_curve,
    )

    predicted = (scores >= threshold).astype(np.int8)
    confusion = confusion_matrix(labels, predicted, labels=[0, 1])
    (_, fp), (fn, tp) = confusion
    overall: dict[str, Any] = {
        "auroc": None,
        "auprc": None,
        "f1": float(2 * tp / (2 * tp + fp + fn)) if tp else 0.0,
        "brier": float(brier_score_loss(labels, scores, pos_label=1)),
        "positive_rate": float(labels.mean()),
        "confusion": confusion.tolist(),
        "threshold": threshold,
    }
    curves: dict[str, list[list[float]]] = {"roc": [], "pr": []}
    warnings = []
    if np.unique(labels).size < 2:
        warnings.append("split has one class; auroc and auprc are null")
    else:
        overall["auroc"] = float(roc_auc_score(labels, scores))
        overall["auprc"] = float(average_precision_score(labels, scores))
        fpr, tpr, _ = roc_curve(labels, scores)
        precision, recall, _ = precision_recall_curve(labels, scores)
        curves["roc"] = _downsample(np.column_stack([fpr, tpr]))
        curves["pr"] = _downsample(np.column_stack([recall, precision]))
    return overall, curves, warnings
