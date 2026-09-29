# Time-Series Guidelines

> Rules for time, resampling, segments, splits, windows, labels, and metrics. These rules prevent data leakage.

---

## Overview

Status: **Verified** for source parsing, preparation, splits, windows, batches, fit statistics, rule labels, and adapter sampling/normalization. Evaluation metrics and run artifacts are also Verified. API time serialization remains Decided.

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

Implementation: `src/tsllm/data/prepare.py::resample`. `tests/data/test_prepare.py` asserts the causal right endpoint, regular-grid completion, `observed`, and the native-frequency path.

- After aggregation, fill the full regular grid. A grid row with no raw record has null channels and `observed = false`.
- Remove duplicate timestamps before resampling with the configured `dedup` rule. The kiln source has 7 duplicate timestamps.
- `src/tsllm/data/source.py::read_source` parses timestamp strings before sorting and deduplication. CSV timestamp columns are read as String even when the text contains only digits. Regression coverage is in `tests/data/test_source.py`.
- Missing values stay null (NaN in numpy arrays). Do not fill them in `tsllm.data`. Each adapter handles NaN in its own way (see `model-adapter-guidelines.md`).

---

## Eligibility and Segments

- `eligible` is the configured rule result. A row is not eligible if a channel in the rule is null.
- A segment starts at an eligible row and ends at an eligible row. Inside a segment, a run of non-eligible or unobserved rows is allowed if it is not longer than `max_gap`. A longer run ends the segment.
- Segments shorter than `min_length` are removed. Rows outside a segment have `segment_id = -1`.
- Segment duration includes both endpoints: `(last_row - first_row + 1) * freq`. Implementation: `src/tsllm/data/prepare.py::assign_segments`; exact-gap and duration tests: `tests/data/test_rules_splits.py`.
- For the kiln config (1 min grid, `max_gap: 2min`, `min_length: 6h`), the user-approved reference is 523,702 eligible minutes (±2%). An independent CSV count found 3,142,212 eligible source rows; dividing by 6 gives the reference. The prepared result has 523,782 eligible minutes and 43 retained segments. The parent research note retains the failed check against the former 460,417-minute reference. Raw and prepared segment counts use different rules.

---

## Splits

- Order is by time only. Never split at random.
- Boundaries come from cumulative eligible counts (default ratios fit 0.70, val 0.10, cal 0.10, test 0.10). Every row gets a split from its time, also rows outside segments.
- Split names are exactly `fit`, `val`, `cal`, `test`.
- `src/tsllm/data/prepare.py::assign_splits` assigns boundary rows to the next split. `tests/data/test_rules_splits.py` checks each cumulative ratio within one eligible row.

---

## Windows

- Origin `o` is the row of the last context step. Context rows are `[o - L + 1, o]`. Target rows are `[o + 1, o + H]`.
- All context and target rows must have the same `segment_id`, and it must not be -1. Rows inside a window need not all be eligible.
- Training origin: all target rows are in `fit`.
- Evaluation origin for split `s`: all target rows are in `s`. The context can be in an earlier split. This uses only past data, so it is not leakage.
- Stride filter: keep origins where `origin_row % stride == 0`. This rule gives the same origin set to every run with the same task config. Do not use a random sample for evaluation origins.
- `max_eval_origins` picks evenly spaced origins with `np.linspace` over the legal list.
- Implementations: `src/tsllm/data/windows.py::build_train_manifest`, `build_eval_manifest`, `context_batch`, `targets`, and `segment_set`. `segment_set` clips segments at the requested split boundary. `targets` returns values and a non-missing/eligible target mask. Tests: `tests/data/test_stats_windows.py`.
- `validate_origins` rechecks extraction boundaries even when a caller supplies origin rows directly. A legal manifest does not remove the extraction-time checks.
- Adapter sampling is implemented in `src/tsllm/backbones/windows.py::sample_training_windows`. Each context and target comes from one `SegmentSet` array. The caller supplies a seeded `np.random.Generator`; short arrays are excluded, and no legal window raises `ValueError`. `tests/backbones/test_baselines.py::test_windows_never_cross_arrays` checks boundaries and deterministic sampling.
- Adapters accept split-clipped `SegmentSet` values from the data layer. They do not read datasets or reconstruct split boundaries. Validation channels must use the same order as training channels. `src/tsllm/backbones/training.py` selects validation windows once with a fixed generator, uses validation only for model selection, and restores the lowest-loss trainable parameters. Regression coverage is in `tests/backbones/test_training.py`.

---

## Fit-Only Statistics

These values use only rows with `split == "fit"` and `eligible == true`:

- `FitStats`: per-channel mean, std, and quantiles 0.01, 0.05, 0.5, 0.95, 0.99.
- Label thresholds given as `{quantile: q}`.
- Normalization inside adapters (they receive `FitStats`).
- Any scaler, PCA, or feature selector in a classification head.

Validation-split use is allowed only for model selection: early stopping, best adapter checkpoint, and the classification decision threshold.

Verified implementations: `src/tsllm/data/stats.py::fit_rows` and `compute_fit_stats`, plus `src/tsllm/data/labels.py::resolve_threshold`. The statistics and label tests inject extremes into every later split and into ineligible fit rows; fitted values must remain unchanged.

---

## Labels

- A `future_event` label at origin `o` uses only target rows `[o + 1, o + W]`. It never uses the context.
- The label is positive if the condition holds for at least `min_duration` consecutive steps inside the window.
- Null target points interrupt the consecutive event. See `src/tsllm/data/labels.py::future_event_labels`. The eligible-row filter applies when fitting quantile thresholds.
- `tests/data/test_labels.py` checks the origin, first target, final target, and the row after the window. The cases detect both a backward-shifted window and an included origin.
- `src/tsllm/tasks/classify.py` writes the rule, the resolved threshold, and per-split sample counts and positive rates to `label_info.json`. `tests/tasks/test_classify_leakage.py` multiplies later-split source values by 1000 and asserts an unchanged threshold that equals the eligible-fit quantile.

---

## Metrics

Implemented in `src/tsllm/evaluation/metrics.py`; hand-computed and sklearn-agreement tests in `tests/evaluation/test_metrics.py`.

- Report errors in physical units per channel (`mae`, `rmse`, `n`).
- Aggregate across channels only after division by the fit std: `mae_norm_macro = mean_c(mae_c / std_fit_c)`. The same rule applies to `rmse_norm_macro`, `pinball`, and `width_80`. List channels with zero or null fit std in `excluded_channels` and exclude them.
- Compute metrics only where the target mask is true and the prediction is finite. `n_missing_predictions` counts observed targets with a non-finite prediction; the task adds a warning when the count is not zero.
- `coverage_80` and `width_80` need both the 0.1 and the 0.9 quantile levels; otherwise they are null.
- Record `origin_set_hash` per split with `tsllm.data.windows.origin_set_hash`. Two runs are comparable on a split only if the hashes are equal. `tests/tasks/test_origin_hash.py` runs `persistence` and `ridge` with one task config and asserts equal hashes.
- Classification: the decision threshold maximizes F1 on the validation split and applies to all splits. A split with one class gives null `auroc` and `auprc` and a warning. A one-class validation split uses threshold 0.5 and a warning.
- Gate: if a foundation model error is more than 2 times the `persistence` error, check units, channel order, and time alignment before you trust the result.
