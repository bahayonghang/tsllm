# Error Handling

> How errors are raised, recorded, and returned.

---

## Overview

- Domain errors inherit `tsllm.errors.TsllmError`. Each class has a stable `code` string.
- Each layer raises the error. Only 2 places catch all errors: the worker entry (`tsllm.runs.worker.main`) and the service exception handlers (`tsllm.service.errors`).
- The worker records a failure in `status.json` and `events.jsonl`. The service returns a failure as the JSON error envelope.

---

## Error Types

```python
# src/tsllm/errors.py (reference pattern)
from typing import ClassVar


class TsllmError(Exception):
    code: ClassVar[str] = "TSLLM_ERROR"
```

Define each subclass in the module that owns the condition. Do not collect all classes in `errors.py`.

| Class                | Module                 | `code`                   | Condition                                                            |
| -------------------- | ---------------------- | ------------------------ | -------------------------------------------------------------------- |
| `DatasetNotFound`    | `tsllm.data.registry`  | `DATASET_NOT_FOUND`      | No `configs/datasets/<id>.yaml`                                      |
| `DatasetConfigError` | `tsllm.data.registry`  | `DATASET_CONFIG_INVALID` | YAML does not validate, or `id` differs from the file name           |
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
- Do not catch an exception only to log it and continue. Catch it only if you can recover or add context. To add context, use `raise NewError(...) from exc`.
- Do not fall back silently. Example: if `mode: lora` and `peft` is not installed, raise `BackboneLoadError`. Do not run `full` instead.
- A bare `except:` is not allowed. `except Exception` is allowed only in `worker.main` and in the service handlers.

---

## Worker Failure

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

## API Error Envelope

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
