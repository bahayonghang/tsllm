# Error Handling

> How errors are raised, recorded, and returned.

---

## Overview

Status: **Verified** for data/adapter/task/run domain exceptions, loading boundaries, worker failure, CLI handling, and the service API envelope.

- Domain errors inherit `tsllm.errors.TsllmError`. Each class has a stable `code` string.
- Each layer raises the error. Only 2 places catch all errors: the worker entry (`tsllm.runs.worker.main`) and the service exception handlers (`tsllm.service.errors`).
- The worker records a failure in `status.json` and `events.jsonl`. The service returns a failure as the JSON error envelope.

---

## Error Types

The base class is `src/tsllm/errors.py::TsllmError`, with `code: ClassVar[str] = "TSLLM_ERROR"`. Data subclasses are implemented in `src/tsllm/data/registry.py` and `src/tsllm/data/cache.py`. Adapter subclasses are in `src/tsllm/backbones/base.py`. Task and run subclasses are in `src/tsllm/tasks/validation.py` and `src/tsllm/runs/store.py`.

Define each subclass in the module that owns the condition. Do not collect all classes in `errors.py`.

| Class                | Module                 | `code`                   | Condition                                                            |
| -------------------- | ---------------------- | ------------------------ | -------------------------------------------------------------------- |
| `DatasetNotFound`    | `tsllm.data.registry`  | `DATASET_NOT_FOUND`      | No `configs/datasets/<id>.yaml`                                      |
| `DatasetConfigError` | `tsllm.data.registry`  | `DATASET_CONFIG_INVALID` | Invalid config/source, filename mismatch, inaccessible storage, or source change during ingestion |
| `DatasetNotIngested` | `tsllm.data.cache`     | `DATASET_NOT_INGESTED`   | Cache is missing or stale                                            |
| `CapabilityError`    | `tsllm.backbones.base` | `CAPABILITY_UNSUPPORTED` | The backbone does not support the mode, embed, or horizon            |
| `BackboneLoadError`  | `tsllm.backbones.base` | `BACKBONE_LOAD_FAILED`   | A library is missing, or the checkpoint cannot be resolved or loaded |
| `TaskConfigError`    | `tsllm.tasks.validation` | `TASK_CONFIG_INVALID` | A split has no legal origins for the task lengths, or training labels have one class |
| `InvalidTransition`  | `tsllm.runs.store`     | `INVALID_TRANSITION`     | `(from, to, writer)` is not in the state table                       |
| `RunNotFound`        | `tsllm.runs.store`     | `RUN_NOT_FOUND`          | No run directory for the id                                          |
| `ChannelError`       | `tsllm.data.registry`  | `CHANNEL_INVALID`        | A requested channel does not exist, or a channel update changes the channel set |
| `TemplateNotFound`   | `tsllm.config.templates` | `TEMPLATE_NOT_FOUND`   | No `configs/runs/<name>.yaml`                                        |
| `ResultNotFound`     | `tsllm.runs.results`   | `RESULT_NOT_FOUND`       | The run has no `metrics.json`, or no predictions for the split       |

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

## Worker Failure

Implemented in `src/tsllm/runs/worker.py::main`.

```python
store.transition(run_id, "running", writer="worker", pid=os.getpid())
reporter = FileReporter(run_dir / "events.jsonl", mirror=mirror)
try:
    ...
    store.transition(run_id, "succeeded", writer="worker")
    return 0
except Exception as exc:
    reporter.log(traceback.format_exc(), level="error")
    summary = " ".join(f"{type(exc).__name__}: {exc}".split())
    store.transition(run_id, "failed", writer="worker", error=summary)
    return 1
```

- The `running` transition is outside `try`. If the run is no longer `queued` (for example `cancelled`), `InvalidTransition` propagates and the process exits non-zero without a state write.
- The full traceback goes to `events.jsonl` (kind `log`, level `error`).
- `status.json.error` holds one line: `<ExceptionClass>: <message>`. Whitespace, including newlines, collapses to single spaces.
- `validate_job` runs inside the worker before data or model loading, and in `tsllm run` before the run directory is created. A job that the CLI rejects creates no directory.
- If the worker process exits with a non-zero code and `status.json` is still `running`, the service writes `failed` with `error = "worker exited with code N"`.
- If the worker process exits and `status.json` is still `queued` (the worker did not write `running`, for example the interpreter did not start), the service writes `queued → failed` with `error = "worker exited with code N before it started"`. `started_at` stays null.
- Tests: `tests/runs/test_worker_e2e.py::test_failure_records_traceback_and_summary` and `tests/runs/test_store.py::test_transition_matrix`.

---

## API Error Envelope

Implemented in `src/tsllm/service/errors.py`. Every non-2xx response has this body:

```json
{
  "error": {
    "code": "DATASET_NOT_INGESTED",
    "message": "dataset 'yangquan_kiln' cache is missing or stale",
    "detail": null
  }
}
```

`tsllm.service.errors.STATUS_BY_CODE` maps codes to HTTP status:

| HTTP status | Codes |
| ----------- | ----- |
| 404 | `DATASET_NOT_FOUND`, `RUN_NOT_FOUND`, `TEMPLATE_NOT_FOUND`, `RESULT_NOT_FOUND`; `NOT_FOUND` for a path without a route |
| 409 | `DATASET_NOT_INGESTED`, `INVALID_TRANSITION` |
| 422 | `VALIDATION_ERROR`, `CAPABILITY_UNSUPPORTED`, `DATASET_CONFIG_INVALID`, `CHANNEL_INVALID`, `TASK_CONFIG_INVALID`, `BACKBONE_LOAD_FAILED`, `NOT_IMPLEMENTED` |
| 500 | Any other exception. `code` is `INTERNAL_ERROR`. The traceback goes to the service log, not to the response. |

- `VALIDATION_ERROR` comes from request validation and from Pydantic validation inside a route (for example an invalid template file). `detail` is a list of `{loc, msg, type}`. Input values are not echoed.
- `BACKBONE_LOAD_FAILED` is 422 at the API because `validate_job` raises it for an unregistered backbone name, which is request input. Checkpoint loading runs only in the worker and is recorded in `status.json`.
- `TASK_CONFIG_INVALID` is 422 for the same reason: the task lengths do not fit the data. The worker normally raises it, so it usually appears in `status.json.error`.
- `NotImplementedError` (a feature the config allows but this round does not implement, for example `past_covariate` channels in a forecast run) maps to 422 with code `NOT_IMPLEMENTED` and the exception message.
- Other Starlette HTTP errors (for example 405) use code `HTTP_ERROR`.
- Routes declare `ErrorOut` for 404, 409, 422, and 500 in OpenAPI (`ERROR_RESPONSES`).

The domain layers do not know HTTP status codes. Only `tsllm.service.errors` holds the mapping.

Tests: `tests/service/test_api_basic.py::test_error_envelopes` covers 404, 409, and 422 codes, including `NOT_IMPLEMENTED` and `BACKBONE_LOAD_FAILED`, and asserts that a rejected submission creates no run directory.

### Service writes and the worker race

`RunStore.transition` reads and then writes without a file lock. `tsllm.service.jobs.JobManager` removes the race with the worker this way:

- Every service state write holds one `asyncio.Lock` in `JobManager`.
- Launch reads `queued` and starts the subprocess under the lock. Cancel of a run without a process writes `cancelled` under the lock; the scheduler skips a run that is no longer `queued`.
- Cancel of a run with a process first terminates the process tree (`psutil`, terminate, then kill after 3 s), then writes `cancelled`. After the process ends, no worker write can follow. If the worker wrote a terminal state first, the transition raises `InvalidTransition` (409).
- After a worker process exits, the service writes `failed` only if the state is still `queued` or `running`: `error = "worker exited with code N"`, with the suffix ` before it started` for `queued`. A run that is being cancelled is skipped.
- Tests: `tests/service/test_api_jobs.py::test_worker_exit_without_final_state_is_failed` and `test_worker_exit_before_running_is_failed`.

## Common Mistakes

- Raising `HTTPException` in a lower layer. Raise a `TsllmError` subclass. The service maps it.
- Returning `None` for "not found". Raise the matching `*NotFound` error.
- Putting a sample of the data in an error message to help debugging. Put the row index or timestamp instead.
