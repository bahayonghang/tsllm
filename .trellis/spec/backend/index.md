# Backend Development Guidelines

> Conventions for the Python package `src/tsllm`.

---

## Status

The data-contract implementation is Verified. Evidence is in `.trellis/tasks/archive/2026-09/09-28-data-contract/verification.md`: all four quality commands pass, 87 synthetic tests pass, and both configured datasets pass local ingestion acceptance.

`Verified` covers the implemented config, data, error, reporting, CLI, and test contracts only. Each guide identifies its implementation files and tests. Adapter, experiment-runner, service, web, and metric contracts remain Decided until their child tasks verify them. The parent `design.md` remains the shared contract.

---

## Guidelines Index

| Guide                                                     | Description                                                          | Status  |
| --------------------------------------------------------- | -------------------------------------------------------------------- | ------- |
| [Directory Structure](./directory-structure.md)           | Config/data modules and dependency boundaries; later layers planned | Verified |
| [Storage Guidelines](./database-guidelines.md)            | YAML registry and Parquet cache; run directories planned             | Verified |
| [Error Handling](./error-handling.md)                     | Data errors and CLI privacy; worker/API handling planned             | Verified |
| [Logging Guidelines](./logging-guidelines.md)             | Reporter and CLI output; file events and worker diagnostics planned   | Verified |
| [Quality Guidelines](./quality-guidelines.md)             | Python gates and synthetic data tests; later-layer tests planned      | Verified |
| [Time-Series Guidelines](./time-series-guidelines.md)     | Data preparation, windows, stats, labels; evaluation metrics planned   | Verified |
| [Model Adapter Guidelines](./model-adapter-guidelines.md) | Backbone protocol, capabilities, lazy imports, checkpoints, NaN      | Decided |

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

- Shared contracts: `.trellis/tasks/09-28-tsfm-platform/design.md`. When a spec rule and the shared contract differ, the shared contract is correct. Update the spec file in the same change.
- Data facts: `.trellis/tasks/09-28-tsfm-platform/research/data-profile.md`.
- Library versions and API facts: `.trellis/tasks/09-28-tsfm-platform/research/library-compatibility.md`.

---

**Language**: Write spec files in English (ASD-STE100 style). Task planning files under `.trellis/tasks/` are in Chinese.
