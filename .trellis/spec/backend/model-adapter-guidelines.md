# Model Adapter Guidelines

> How to write a backbone adapter in `src/tsllm/backbones/`.

---

## Overview

Status: **Verified** for the six implemented adapters, configuration, capabilities, lazy discovery, checkpoint resolution, NaN handling, training, and adapter round trips. Offline tests and local real-checkpoint/CUDA acceptance are recorded in `.trellis/tasks/archive/2026-09/09-28-backbone-adapters/verification.md` and its `research/real-acceptance.md`. Runner, service, and web integration remain Decided.

An adapter wraps one time-series model (a foundation model or a baseline) behind the `Backbone` protocol. Tasks, evaluation, service, and web code use only the protocol, the registry, and `Capabilities`. They never use a model name in a condition.

The contract is in the parent design §5. Adapter details are in `.trellis/tasks/archive/2026-09/09-28-backbone-adapters/design.md` §2–§4.

---

## Protocol

```python
class Backbone:
    name: ClassVar[str]
    capabilities: ClassVar[Capabilities]
    Options: ClassVar[type[BaseModel]]
    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None, *,
             reporter: Reporter) -> None: ...
    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput: ...   # mean (B, C, H), physical units
    def finetune(self, train: SegmentSet, val: SegmentSet | None, cfg: FinetuneConfig,
                 context_length: int, horizon: int, reporter: Reporter, *,
                 mode: Literal["lora", "head", "full"]) -> None: ...
    def embed(self, batch: ContextBatch) -> np.ndarray: ...                         # (B, D)
    def save_adapter(self, path: Path) -> None: ...
    def load_adapter(self, path: Path) -> None: ...
```

- A method that the adapter does not support raises `CapabilityError`.
- `Capabilities` must match the code. If `embed` is `False`, `embed()` raises. If `"lora"` is not in `forecast_modes`, `finetune()` raises for `mode: lora`.
- `forecast()` input and output are in physical units. Normalization happens inside the adapter.
- Pass `RunConfig.mode` to the required `finetune(mode=...)` argument. Validate the mode before training. Do not add a second serialized mode field or select a default training mode.
- `load(..., reporter=...)` stores the caller's Reporter for load and embed warnings. `finetune` uses its explicit Reporter argument.
- An adapter does not read dataset files, does not know split names, and does not write to the run directory. It writes only to the `path` given to `save_adapter`.

---

## Registration and Lazy Imports

```python
# Implemented in src/tsllm/backbones/timesfm25.py (excerpt).
from typing import ClassVar
from tsllm.backbones.base import Backbone, Capabilities
from tsllm.backbones.registry import register_backbone


@register_backbone(requires=["torch", "transformers", "peft"],
                   license="Apache-2.0",
                   default_checkpoint="google/timesfm-2.5-200m-transformers")
class TimesFm25Backbone(Backbone):
    name: ClassVar[str] = "timesfm25"
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"zero_shot", "lora"}, embed=True, quantiles=True,
        multivariate="channel_independent", max_context=None, max_horizon=None,
        needs_fit_stats=False,
    )

```

The concrete `load` method imports `TimesFm2_5ModelForPrediction` inside the method. The complete registration includes the pinned model-card URL. `tests/backbones/test_contract.py::test_registry_import_is_light` runs discovery in a fresh process and checks all six heavy import names. `tests/backbones/test_registry.py` checks the capability matrix and schema serialization.

- The module top level imports only the standard library, numpy, pydantic, and `tsllm` modules.
- `backbones/__init__.py` imports every adapter module so that registration runs.
- `BackboneInfo.installed` comes from `importlib.util.find_spec` for each name in `requires`. It must not import the library.
- Test: after `import tsllm.backbones` and `list_backbones()`, `"torch"` is not in `sys.modules`.

---

## Options

- Each adapter defines `class Options(StrictModel)` with defaults and a `description` on every field. The web form uses this schema.
- `load()` validates `cfg.options` with `Options` first.
- Put model-specific settings in `Options`: batch sizes, quantile levels, pooling. Do not add model-specific fields to `BackboneConfig` or `FinetuneConfig`.

---

## Mode and Reporter Contract

### 1. Scope / Trigger

Status: **Verified** for adapters and their tests. The user approved these protocol changes during backbone-adapters implementation. The planned runner uses the same signatures; runner execution remains Decided. Data containers and the Reporter protocol do not change.

### 2. Signatures

- `load(cfg, fit_stats, *, reporter)` requires a caller-provided Reporter.
- `finetune(train, val, cfg, context_length, horizon, reporter, *, mode)` requires `mode` to be `lora`, `head`, or `full`.

### 3. Contracts

- `RunConfig.mode` remains the only serialized mode field. Pass the value without transformation.
- Store the Reporter passed to `load` for checkpoint and embed warnings. Do not create a replacement Reporter or use global mutable reporting state.
- Chronos passes the selected mode unchanged to `fit(finetune_mode=mode)`. A missing LoRA dependency must not select full training.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Mode is absent from `forecast_modes` | Raise `CapabilityError` before parameter updates |
| LoRA dependency cannot be imported | Raise `BackboneLoadError` before training |
| Checkpoint revision is not specified | Report a warning and expose the resolved revision |
| Features input has an all-NaN channel | Emit zero features and report the affected channel count |

### 5. Good / Base / Bad Cases

- Good: Chronos receives explicit `lora` or `full` and trains in that mode.
- Base: A zero-shot run calls `load` and `forecast` without `finetune`.
- Bad: A caller requests TTM LoRA. The adapter raises `CapabilityError`.

### 6. Tests Required

- Assert the mode passed to Chronos equals the caller's mode for both supported training modes.
- Assert an unsupported mode fails before weights change.
- Capture the injected Reporter and assert checkpoint warnings and features missing-channel counts.
- Keep the isolated registry import test and data leakage tests passing.
- Implementation: `src/tsllm/backbones/base.py`, `chronos2.py`, and `features.py`. Assertions: `tests/backbones/test_contract.py`, `test_chronos2_tiny.py`, and `test_baselines.py`.

### 7. Wrong vs Correct

Wrong: select a training mode from adapter defaults, or discard a caller-provided Reporter.

Correct: call `backbone.load(cfg, fit_stats, reporter=reporter)` and `backbone.finetune(train, val, cfg, L, H, reporter, mode=run_mode)`.

## Checkpoints and Weights

- Resolve with `tsllm.backbones.checkpoint.resolve_checkpoint(cfg)`. It accepts a Hugging Face repo id or a local directory. It returns the local path, the resolved revision (commit hash), and the source.
- `huggingface.co` is not reachable from this machine. Set `HF_ENDPOINT=https://hf-mirror.com` or use a local directory. Do not hard-code the mirror in code.
- If `revision` is `null`, warn through the injected Reporter and expose `resolved_checkpoint.revision`. Writing `env.json` belongs to the planned experiment runner.
- Default checkpoints: `amazon/chronos-2`, `google/timesfm-2.5-200m-transformers`, `ibm-granite/granite-timeseries-ttm-r2`.
- Do not add TimesFM-3. Its license does not allow this use. Record `license` and `license_url` for foundation-model adapters. The 2026-09-29 model-card audit confirms Apache-2.0 for the three pinned cards; see the child task's `research/library-api-audit.md`. Baselines have no external model-card license.

### Locked-library boundaries

- `src/tsllm/backbones/timesfm25.py::_context_length` rounds the internal length up to a patch boundary. The library applies left padding and its mask. The adapter keeps the caller's original observations and horizon. `tests/backbones/test_timesfm25_tiny.py::test_timesfm_shape_nan_and_non_patch_context` covers L=30 with patch length 8.
- TTM selects an HF model key from requested L/H before resolving the snapshot. `src/tsllm/backbones/ttm.py::_model_metadata` maps that key to the library's branch; an explicit revision bypasses automatic selection. A model key such as `512-96-r2` is not a branch name.
- TTM passes a nonempty revision to the local library call. A local directory with unknown revision keeps `resolved_checkpoint.revision=None`; the internal `local` placeholder is not provenance. Native context cropping or padding is reported with requested and effective length metrics. `tests/backbones/test_ttm_tiny.py` covers these boundaries.
- TTM adapter metadata retains the initial checkpoint-selection L/H, channel order, and resolved revision. Later forecasts with another supported L/H do not replace that identity. Reload rejects a known revision mismatch. `tests/backbones/test_ttm_tiny.py::test_ttm_save_preserves_loaded_selection_dimensions` covers forecast-before-save and revision mismatch.
- TTM checkpoints with `resolution_prefix_tuning` require a frequency token. Use the existing `ContextBatch.freq` or `SegmentSet.freq` and the locked library's `TimeSeriesPreprocessor.get_frequency_token`. Pass a same-device long tensor with shape `(B,)`. Keep the library's frequency normalization and OOV=0 semantics; report an OOV warning through the injected Reporter. Reject invalid frequencies, out-of-vocabulary-range tokens, and a validation frequency that differs from the training frequency. Do not change the selected checkpoint to avoid a required input.
  Implementation: `src/tsllm/backbones/ttm.py::_frequency_token` and `_inputs`; prefix-enabled tiny-model regressions: `tests/backbones/test_ttm_tiny.py`. The real acceptance record retains the missing-token failure and the successful rerun on the same checkpoint revision.
- transformers 5.17.0 TimesFM uses its built-in training loss. The model's quantile-loss column indices differ from its exported quantile mapping. The API audit records that library limitation. Do not replace the loss definition without a shared-design decision.

---

## NaN and Normalization

Context arrays contain NaN for missing values. Each adapter states its rule in the module docstring. The rules for this round:

| Adapter       | NaN rule                                                                                                                     | Normalization  |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------- |
| `persistence` | Last non-NaN value; all NaN → NaN output                                                                                     | None           |
| `ridge`       | NaN → 0 after fit-stat normalization; drop training samples with NaN targets                                                 | `FitStats`     |
| `features`    | nan-aware statistics; all-NaN channel → 0 and a warning count                                                                | None           |
| `chronos2`    | Pass NaN to the model                                                                                                        | Model internal |
| `timesfm25`   | Strip leading NaN, interpolate inner NaN, fill trailing NaN with last value; all-NaN channel → NaN output, not sent to model | Model internal |
| `ttm`         | Forward fill, then backward fill, then 0 after normalization                                                                 | `FitStats`     |

If an adapter needs `FitStats`, set `needs_fit_stats=True`. `FitStats` comes from fit rows only (see `time-series-guidelines.md`).

---

## Fine-Tuning

- Sample training windows only inside the fit `SegmentSet` with `backbones/windows.py` and the caller's `np.random.Generator`. A window never crosses an array boundary.
- Validation uses a fixed window set from `val` (fixed seed). Keep the adapter weights with the lowest validation loss.
- `mode: lora` needs `peft`. If `peft` is missing, raise `BackboneLoadError`.
- After you add LoRA, report `trainable_params` and `total_params` with `reporter.metric`. A LoRA run where `trainable_params == total_params` is a bug.
- On CUDA, use bf16 autocast when `dtype: bf16`. The GPU is sm_120 (RTX 5090 Laptop, 24,463 MiB); torch must be a CUDA 12.8 or later build.
- Share the training loop in `backbones/training.py` (`timesfm25`, `ttm`). Chronos-2 uses `Chronos2Pipeline.fit`.

---

## Tests for a New Adapter

1. Registry test: the adapter is listed, `Options` schema serializes, no heavy import.
2. Offline test with a tiny random model built from a config: output shape `(B, C, H)`, NaN input, loss decreases over a few steps, `save_adapter` → `load_adapter` gives the same output.
3. `@pytest.mark.weights` smoke test with the real checkpoint: load, forecast, 5 fine-tune steps.
4. `@pytest.mark.gpu` test: CUDA + bf16 zero-shot forecast.

Concrete tests are in `tests/backbones/test_baselines.py`, `test_contract.py`, `test_registry.py`, `test_training.py`, the three `test_*_tiny.py` files, `test_smoke_weights.py`, and `test_cuda.py`. Real acceptance uses only synthetic series. `weights` and `gpu` tests fail when prerequisites are unavailable; they do not skip a mandatory acceptance item. Store first failures separately from corrected reruns and record the actual loaded revision, elapsed time, and peak allocated VRAM.

---

## Adding an Adapter: Checklist

- [ ] New module `backbones/<name>.py`, registered, no top-level heavy import.
- [ ] `Capabilities` match the implemented methods.
- [ ] `Options` model with descriptions.
- [ ] NaN rule and license in the module docstring.
- [ ] Dependency added with `uv add` and compatible with Python 3.13 and torch 2.11.
- [ ] Tests 1–2 pass offline. Tests 3–4 pass on the GPU machine.
- [ ] No change in `tsllm.tasks`, `tsllm.service`, or `web/` was necessary. If one was necessary, the protocol is missing something: update the parent design §5 first.
