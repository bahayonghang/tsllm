# Backend Development Guidelines

> Conventions for the Python package `src/tsllm`.

---

## Status

The data-contract implementation is Verified. Evidence is in `.trellis/tasks/archive/2026-09/09-28-data-contract/verification.md`: all four quality commands pass, 87 synthetic tests pass, and both configured datasets pass local ingestion acceptance.

The backbone-adapters implementation is also Verified for its six adapters, config, registry, checkpoint, training, and save/load contracts. Its offline and local real-checkpoint/CUDA evidence is in `.trellis/tasks/archive/2026-09/09-28-backbone-adapters/verification.md`. The first TTM real-checkpoint failure and the corrected rerun are retained.

The experiment-runner implementation is Verified for run config and schema, metrics, run store, file events, worker, tasks, and the run CLI. Offline tests cover synthetic end-to-end runs; local CLI acceptance on the kiln dataset is recorded in `.trellis/tasks/archive/2026-09/09-28-experiment-runner/prd.md`.

The service-api implementation is Verified for the HTTP API, error envelope, job queue, cancel, restart recovery, SSE, and CLI. Offline tests are in `tests/service/`; local manual acceptance is recorded in `.trellis/tasks/archive/2026-09/09-28-service-api/prd.md`.

`Verified` covers only the implemented scopes identified in each guide and their tests. Web contracts are Verified for the implemented web-ui scope. Evidence is in `.trellis/tasks/archive/2026-09/09-28-web-ui/prd.md` and the frontend guides. The parent `design.md` remains the shared contract.

---

## Guidelines Index

| Guide                                                     | Description                                                          | Status  |
| --------------------------------------------------------- | -------------------------------------------------------------------- | ------- |
| [Directory Structure](./directory-structure.md)           | Config/data/adapter/task/evaluation/run modules and dependency boundaries; service; web | Verified |
| [Storage Guidelines](./database-guidelines.md)            | YAML registry, Parquet cache, and run directories; service config writes | Verified |
| [Error Handling](./error-handling.md)                     | Data/adapter/task/run errors, worker failure, CLI privacy; API envelope; service/worker race | Verified |
| [Logging Guidelines](./logging-guidelines.md)             | Reporter, adapter metrics, CLI, file events, environment snapshot; SSE; service logging | Verified |
| [Quality Guidelines](./quality-guidelines.md)             | Offline gates, adapter regressions, runner end-to-end tests, real weight/CUDA acceptance; service tests | Verified |
| [Time-Series Guidelines](./time-series-guidelines.md)     | Data preparation, windows, stats, labels, adapter sampling, evaluation metrics | Verified |
| [Model Adapter Guidelines](./model-adapter-guidelines.md) | Six adapters, capabilities, lazy imports, checkpoints, NaN, training | Verified |

---

## Pre-Development Checklist

Read these files before you write code in a layer:

| Layer                             | Read                                                             |
| --------------------------------- | ---------------------------------------------------------------- |
| `tsllm.config`                    | directory-structure, quality-guidelines                          |
| `tsllm.data`                      | time-series-guidelines, database-guidelines, error-handling      |
| `tsllm.backbones`                 | model-adapter-guidelines, time-series-guidelines, error-handling |
| `tsllm.tasks`, `tsllm.evaluation` | time-series-guidelines, logging-guidelines                       |
| `tsllm.runs`                      | database-guidelines, logging-guidelines, error-handling          |
| `tsllm.service`                   | error-handling, logging-guidelines, directory-structure          |

Also read `.trellis/spec/guides/index.md` when a change crosses two or more layers.

---

## Source Documents

- Shared contracts: `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md`. When a spec rule and the shared contract differ, the shared contract is correct. Update the spec file in the same change.
- Data facts: `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/research/data-profile.md`.
- Library versions and API facts: `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/research/library-compatibility.md`.

---

**Language**: Write spec files in English (ASD-STE100 style). Task planning files under `.trellis/tasks/` are in Chinese.
