# Model Adapter Guidelines

> How to write a backbone adapter in `src/tsllm/backbones/`.

---

## Overview

An adapter wraps one time-series model (a foundation model or a baseline) behind the `Backbone` protocol. Tasks, evaluation, service, and web code use only the protocol, the registry, and `Capabilities`. They never use a model name in a condition.

The contract is in the parent design §5. Adapter details are in `.trellis/tasks/09-28-backbone-adapters/design.md` §2–§4.

---

## Protocol

```python
class Backbone(Protocol):
    name: ClassVar[str]
    capabilities: ClassVar[Capabilities]
    Options: ClassVar[type[BaseModel]]
    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None) -> None: ...
    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput: ...   # mean (B, C, H), physical units
    def finetune(self, train: SegmentSet, val: SegmentSet | None, cfg: FinetuneConfig,
                 context_length: int, horizon: int, reporter: Reporter) -> None: ...
    def embed(self, batch: ContextBatch) -> np.ndarray: ...                         # (B, D)
    def save_adapter(self, path: Path) -> None: ...
    def load_adapter(self, path: Path) -> None: ...
```

- A method that the adapter does not support raises `CapabilityError`.
- `Capabilities` must match the code. If `embed` is `False`, `embed()` raises. If `"lora"` is not in `forecast_modes`, `finetune()` raises for `mode: lora`.
- `forecast()` input and output are in physical units. Normalization happens inside the adapter.
- An adapter does not read dataset files, does not know split names, and does not write to the run directory. It writes only to the `path` given to `save_adapter`.

---

## Registration and Lazy Imports

```python
# src/tsllm/backbones/timesfm25.py (reference pattern)
from typing import ClassVar
from tsllm.backbones.base import Capabilities
from tsllm.backbones.registry import register_backbone


@register_backbone(requires=["torch", "transformers", "peft"],
                   license=LICENSE,  # copy from the model card at the pinned revision
                   default_checkpoint="google/timesfm-2.5-200m-transformers")
class TimesFm25Backbone:
    name: ClassVar[str] = "timesfm25"
    capabilities: ClassVar[Capabilities] = Capabilities(
        forecast_modes={"zero_shot", "lora"}, embed=True, quantiles=True,
        multivariate="channel_independent", max_context=None, max_horizon=None,
        needs_fit_stats=False,
    )

    def load(self, cfg, fit_stats):
        from transformers import TimesFm2_5ModelForPrediction  # import here, not at top
        ...
```

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

## Checkpoints and Weights

- Resolve with `tsllm.backbones.checkpoint.resolve_checkpoint(cfg)`. It accepts a Hugging Face repo id or a local directory. It returns the local path, the resolved revision (commit hash), and the source.
- `huggingface.co` is not reachable from this machine. Set `HF_ENDPOINT=https://hf-mirror.com` or use a local directory. Do not hard-code the mirror in code.
- If `revision` is `null`, log a warning and record the resolved commit in `env.json`.
- Default checkpoints: `amazon/chronos-2`, `google/timesfm-2.5-200m-transformers`, `ibm-granite/granite-timeseries-ttm-r2`.
- Do not add TimesFM-3. Its license does not allow this use. Record `license` and `license_url` for every adapter. Copy the value from the model card at the pinned revision. On 2026-09-28 only Chronos-2 (Apache-2.0) was confirmed; TimesFM 2.5 and Granite TTM must be checked at implementation.

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

---

## Adding an Adapter: Checklist

- [ ] New module `backbones/<name>.py`, registered, no top-level heavy import.
- [ ] `Capabilities` match the implemented methods.
- [ ] `Options` model with descriptions.
- [ ] NaN rule and license in the module docstring.
- [ ] Dependency added with `uv add` and compatible with Python 3.13 and torch 2.11.
- [ ] Tests 1–2 pass offline. Tests 3–4 pass on the GPU machine.
- [ ] No change in `tsllm.tasks`, `tsllm.service`, or `web/` was necessary. If one was necessary, the protocol is missing something: update the parent design §5 first.
