# Time-Series Guidelines

> Rules for time, resampling, segments, splits, windows, labels, and metrics. These rules prevent data leakage.

---

## Overview

The data contract is in the parent design §3.1 and §4 (`.trellis/tasks/09-28-tsfm-platform/design.md`). This file states the rules that every layer must keep. If code breaks one of these rules, the metrics are not valid.

---

## Time

- Source timestamps have no time zone (the kiln data uses plant local time). Keep them naive (`datetime[us]`, no tz). Do not convert to UTC. Do not attach a zone.
- The API sends data times as ISO strings without an offset. The web UI shows them unchanged.
- System times (`created_at`, `finished_at`, event `ts`) are UTC with an offset. Do not mix the two kinds in one field.
- Durations in config are strings (`10s`, `1min`, `2min`, `6h`) parsed by the `Duration` type in `tsllm.config.base`.
- Lengths in a `RunConfig` (`context_length`, `horizon`, `window`, `min_duration`, strides) are counts of steps at `dataset.freq`. They are not durations.

---

## Resampling

- Right-labeled, right-closed: the value at `T` aggregates the raw records in `(T - freq, T]`. The value at `T` never uses a record after `T`.

```python
# Reference pattern (data-contract design §3)
frame.group_by_dynamic("time", every=freq, closed="right", label="right").agg(...)
```

- After aggregation, fill the full regular grid. A grid row with no raw record has null channels and `observed = false`.
- Remove duplicate timestamps before resampling with the configured `dedup` rule. The kiln source has 7 duplicate timestamps.
- Missing values stay null (NaN in numpy arrays). Do not fill them in `tsllm.data`. Each adapter handles NaN in its own way (see `model-adapter-guidelines.md`).

---

## Eligibility and Segments

- `eligible` is the configured rule result. A row is not eligible if a channel in the rule is null.
- A segment starts at an eligible row and ends at an eligible row. Inside a segment, a run of non-eligible or unobserved rows is allowed if it is not longer than `max_gap`. A longer run ends the segment.
- Segments shorter than `min_length` are removed. Rows outside a segment have `segment_id = -1`.
- For the kiln config (1 min grid, `max_gap: 2min`, `min_length: 6h`), the expected eligible total is about 460,417 minutes (±2%). The raw source has 98 running segments; 35 of them are 24 h or longer.

---

## Splits

- Order is by time only. Never split at random.
- Boundaries come from cumulative eligible counts (default ratios fit 0.70, val 0.10, cal 0.10, test 0.10). Every row gets a split from its time, also rows outside segments.
- Split names are exactly `fit`, `val`, `cal`, `test`.

---

## Windows

- Origin `o` is the row of the last context step. Context rows are `[o - L + 1, o]`. Target rows are `[o + 1, o + H]`.
- All context and target rows must have the same `segment_id`, and it must not be -1. Rows inside a window need not all be eligible.
- Training origin: all target rows are in `fit`.
- Evaluation origin for split `s`: all target rows are in `s`. The context can be in an earlier split. This uses only past data, so it is not leakage.
- Stride filter: keep origins where `origin_row % stride == 0`. This rule gives the same origin set to every run with the same task config. Do not use a random sample for evaluation origins.
- `max_eval_origins` picks evenly spaced origins with `np.linspace` over the legal list.

---

## Fit-Only Statistics

These values use only rows with `split == "fit"` and `eligible == true`:

- `FitStats`: per-channel mean, std, and quantiles 0.01, 0.05, 0.5, 0.95, 0.99.
- Label thresholds given as `{quantile: q}`.
- Normalization inside adapters (they receive `FitStats`).
- Any scaler, PCA, or feature selector in a classification head.

Validation-split use is allowed only for model selection: early stopping, best adapter checkpoint, and the classification decision threshold.

---

## Labels

- A `future_event` label at origin `o` uses only target rows `[o + 1, o + W]`. It never uses the context.
- The label is positive if the condition holds for at least `min_duration` consecutive steps inside the window.
- Write the rule, the threshold, and per-split positive rates to `label_info.json`.

---

## Metrics

- Report errors in physical units per channel (`mae`, `rmse`).
- Aggregate across channels only after division by the fit std: `mae_norm_macro = mean_c(mae_c / std_fit_c)`. List channels with zero fit std and exclude them.
- Compute metrics only where the target mask is true.
- Record `origin_set_hash` per split. Two runs are comparable on a split only if the hashes are equal.
- Gate: if a foundation model error is more than 2 times the `persistence` error, check units, channel order, and time alignment before you trust the result.
