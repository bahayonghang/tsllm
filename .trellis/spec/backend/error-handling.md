# Error Handling

> How errors are raised, recorded, and returned.

---

## Overview

Status: **Verified** for data/adapter domain exceptions, loading boundaries, and CLI handling. Worker failure and API envelope contracts remain Decided.

- Domain errors inherit `tsllm.errors.TsllmError`. Each class has a stable `code` string.
- Each layer raises the error. Only 2 places catch all errors: the worker entry (`tsllm.runs.worker.main`) and the service exception handlers (`tsllm.service.errors`).
- The worker records a failure in `status.json` and `events.jsonl`. The service returns a failure as the JSON error envelope.

---

## Error Types

The base class is `src/tsllm/errors.py::TsllmError`, with `code: ClassVar[str] = "TSLLM_ERROR"`. Data subclasses are implemented in `src/tsllm/data/registry.py` and `src/tsllm/data/cache.py`. Adapter subclasses are in `src/tsllm/backbones/base.py`. Run classes in the table below remain planned.

Define each subclass in the module that owns the condition. Do not collect all classes in `errors.py`.

| Class                | Module                 | `code`                   | Condition                                                            |
| -------------------- | ---------------------- | ------------------------ | -------------------------------------------------------------------- |
| `DatasetNotFound`    | `tsllm.data.registry`  | `DATASET_NOT_FOUND`      | No `configs/datasets/<id>.yaml`                                      |
| `DatasetConfigError` | `tsllm.data.registry`  | `DATASET_CONFIG_INVALID` | Invalid config/source, filename mismatch, inaccessible storage, or source change during ingestion |
| `DatasetNotIngested` | `tsllm.data.cache`     | `DATASET_NOT_INGESTED`   | Cache is missing or stale                                            |
| `CapabilityError`    | `tsllm.backbones.base` | `CAPABILITY_UNSUPPORTED` | The backbone does not support the mode, embed, or horizon            |
| `BackboneLoadError`  | `tsllm.backbones.base` | `BACKBONE_LOAD_FAILED`   | A library is missing, or the checkpoint cannot be resolved or loaded |
| `InvalidTransition`  | `tsllm.runs.store`     | `INVALID_TRANSITION`     | `(from, to, writer)` is not in the state table                       |
| `RunNotFound`        | `tsllm.runs.store`     | `RUN_NOT_FOUND`          | No run directory for the id                                          |

Use `NotImplementedError` for a feature that the config allows but this round does not implement (for example `past_covariate` channels). The message names the feature.

Use `ValueError` only for programming errors inside one module (wrong array shape from a caller in the same package). Do not use it for user input. Pydantic validates user input.

---

## Rules

- Raise early at the boundary. Validate a `RunConfig` against backbone capabilities before the worker loads a model.
- An error message names the identifiers: dataset id, run id, channel name, backbone name, checkpoint. It does not contain data values.
- Do not catch an exception only to log it and continue. Catch it only if you can recover or add context. Chain with `raise NewError(...) from exc` only when the cause contains no private values. At source/config/cache parser boundaries, use a sanitized domain message and `raise ... from None`; parser and validation diagnostics can expose source values.
- Do not fall back silently. Example: if `mode: lora` and `peft` is not installed, raise `BackboneLoadError`. Do not run `full` instead.
- A bare `except:` is not allowed. `except Exception` is allowed only in `worker.main` and in the service handlers.

---

## Verified CLI and Parser Boundaries

- `src/tsllm/cli.py::_domain_errors` catches `TsllmError`, emits its stable code and message, and exits with code 1. It does not catch arbitrary exceptions.
- `src/tsllm/cli.py` disables Typer local-variable display with `pretty_exceptions_show_locals=False` on both apps.
- `src/tsllm/data/source.py::read_source`, `src/tsllm/data/registry.py::load_dataset`, and the cache read/write boundary suppress unsafe parser causes.
- `tests/data/test_source.py` and `tests/test_cli.py` assert that malformed synthetic values do not appear in formatted exception chains or CLI output. `tests/data/test_ingest.py` covers inaccessible and changing sources.

## Adapter Loading Boundaries

- `src/tsllm/backbones/checkpoint.py::checkpoint_loading` converts known import, filesystem, value, and runtime failures at model-loading boundaries to `BackboneLoadError`. The message names the adapter and checkpoint. Do not catch arbitrary exceptions or continue with another model or training mode.
- Validate adapter Options and required FitStats before loading. An unsupported fine-tuning mode raises `CapabilityError` before parameter updates. A missing or broken peft import raises `BackboneLoadError`; a module-spec check alone does not prove that peft can import.
- `tests/backbones/test_contract.py::test_invalid_model_checkpoint_is_domain_error` covers all three foundation models with an invalid local checkpoint. `test_missing_model_dependency_is_domain_error` covers unavailable dependencies. `tests/backbones/test_chronos2_tiny.py` covers the no-full-fallback rule.
- A validation channel-order mismatch is a caller programming error. `src/tsllm/backbones/training.py` rejects the mismatch before optimization; `tests/backbones/test_training.py` checks unchanged parameters and absent progress.

## Worker Failure (Planned)

```python
# tsllm.runs.worker.main (reference pattern, experiment-runner design §8)
try:
    ...
    store.transition(run_id, "succeeded", writer="worker")
    return 0
except Exception as exc:
    reporter.log(traceback.format_exc(), level="error")
    store.transition(run_id, "failed", writer="worker", error=f"{type(exc).__name__}: {exc}")
    return 1
```

- The full traceback goes to `events.jsonl` (kind `log`, level `error`).
- `status.json.error` holds one line: `<ExceptionClass>: <message>`.
- If the worker process exits with a non-zero code and `status.json` is still `running`, the service writes `failed` with `error = "worker exited with code N"`.

---

## API Error Envelope (Planned)

Every non-2xx response has this body:

```json
{
  "error": {
    "code": "DATASET_NOT_INGESTED",
    "message": "dataset 'yangquan_kiln' is not ingested",
    "detail": null
  }
}
```

`tsllm.service.errors` maps codes to HTTP status:

| HTTP status | Codes                                                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 404         | `DATASET_NOT_FOUND`, `RUN_NOT_FOUND`, `TEMPLATE_NOT_FOUND`                                                                     |
| 409         | `DATASET_NOT_INGESTED`, `INVALID_TRANSITION`                                                                                   |
| 422         | `VALIDATION_ERROR` (Pydantic; `detail` is the error list with field paths), `CAPABILITY_UNSUPPORTED`, `DATASET_CONFIG_INVALID` |
| 500         | Any other exception. `code` is `INTERNAL_ERROR`. The traceback goes to the service log, not to the response.                   |

The domain layers do not know HTTP status codes. Only `tsllm.service.errors` holds the mapping.

---

## Common Mistakes

- Raising `HTTPException` in a lower layer. Raise a `TsllmError` subclass. The service maps it.
- Returning `None` for "not found". Raise the matching `*NotFound` error.
- Putting a sample of the data in an error message to help debugging. Put the row index or timestamp instead.
