# Backend Development Guidelines

> Conventions for the Python package `src/tsllm`.

---

## Status

The team decided these conventions on 2026-09-28, before the implementation code exists. The source is the planning task `.trellis/tasks/09-28-tsfm-platform/` (`prd.md`, `design.md`) and its 5 child tasks.

The examples in these files are reference patterns from the task designs. When an implementation child lands, replace each reference example with a real file path and update the Status column below to `Verified`.

---

## Guidelines Index

| Guide                                                     | Description                                                          | Status  |
| --------------------------------------------------------- | -------------------------------------------------------------------- | ------- |
| [Directory Structure](./directory-structure.md)           | Package layers, module placement, naming                             | Decided |
| [Storage Guidelines](./database-guidelines.md)            | No database. YAML configs, Parquet cache, run directories            | Decided |
| [Error Handling](./error-handling.md)                     | `TsllmError` codes, worker failure, API error envelope               | Decided |
| [Logging Guidelines](./logging-guidelines.md)             | `Reporter` events, stdlib logging, data that must not be logged      | Decided |
| [Quality Guidelines](./quality-guidelines.md)             | uv, ruff, pyright, pytest markers, offline tests, forbidden patterns | Decided |
| [Time-Series Guidelines](./time-series-guidelines.md)     | Resampling, segments, splits, windows, leakage rules, metrics        | Decided |
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
