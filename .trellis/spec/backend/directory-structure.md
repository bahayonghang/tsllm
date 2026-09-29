# Directory Structure

> How the Python package `src/tsllm` is organized.

---

## Overview

Status: **Verified** for config, data, adapters, errors, reporting, and the data CLI. The other layers below are planned and remain Decided.

The project is one Python package, `tsllm`, in a `src/` layout. uv builds it with `uv_build`. The design defines 7 layers. Dependencies go down only (see "Layer Rules").

Configuration files (YAML) live in `configs/`. Generated data lives in `cache/` and `runs/`. The web UI lives in `web/` (see `.trellis/spec/frontend/`).

---

## Directory Layout

```text
pyproject.toml
configs/
  datasets/<id>.yaml          # one DatasetConfig per file; file name == id
  runs/<name>.yaml            # planned: RunConfig samples and templates
src/tsllm/
  __init__.py                 # main() calls cli.app()
  cli.py                      # typer entry point: data list, ingest, profile
  errors.py                   # TsllmError base class
  reporting.py                # Reporter protocol, NullReporter, PrintReporter
  config/                     # Pydantic models and YAML io
    base.py  io.py  dataset.py  labels.py
    backbone.py                # BackboneConfig, FinetuneConfig, LoraSpec
    run.py  schema.py           # planned
  data/                       # source read, resample, segments, splits, windows, labels, cache
    types.py  registry.py  source.py  rules.py  prepare.py  cache.py
    stats.py  windows.py  labels.py  profile.py
  backbones/                  # adapter base, registry, and six adapters
    base.py  registry.py  checkpoint.py  windows.py  nan.py  training.py
    persistence.py  ridge.py  features.py  chronos2.py  timesfm25.py  ttm.py
  tasks/                      # planned: task registry and pipelines
    registry.py  context.py  forecast.py  classify.py
  evaluation/                 # planned: metrics and resource measurement
    metrics.py  resources.py
  runs/                       # planned: run store, file reporter, worker entry
    store.py  reporter.py  env.py  seeding.py  worker.py
  service/                    # planned: FastAPI app, job manager, SSE, routes
    app.py  settings.py  errors.py  models.py  jobs.py  sse.py  static.py
    routes/{system,schema,datasets,backbones,runs,compare,templates}.py
tests/                        # mirrors src/tsllm; fixtures make synthetic data
web/                          # planned: React UI
cache/                        # Parquet cache (gitignored)
runs/                         # run directories (gitignored)
data/  ref/                   # raw data and research pack (gitignored, never commit)
```

---

## Layer Rules

```text
service ─▶ runs ─▶ tasks, evaluation ─▶ backbones ─▶ data ─▶ config
                                                        (config, errors, reporting: all layers)
```

- A module imports only from its own layer or lower layers.
- `tsllm.data` does not import torch or any model library.
- `tsllm.service` does not import torch or any model library. Training and inference run only in the worker subprocess. The service must start on a machine without a GPU.
- Model libraries (`chronos`, `transformers`, `tsfm_public`, `peft`, `torch`) are imported only inside adapter methods. Importing `tsllm.backbones.registry` must not import them.
- `tsllm.backbones` gets data only as `ContextBatch` and `SegmentSet`. An adapter does not read files and does not know split names.
- Route functions in `tsllm.service.routes` validate input, call lower layers, and build responses. Put business logic in `runs`, `data`, or `config`.

---

## Where New Code Goes

| New item         | Location                                                                              | Also update                                                                   |
| ---------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Dataset          | `configs/datasets/<id>.yaml`                                                          | Nothing. Code changes are not allowed for a new dataset.                      |
| Backbone adapter | `src/tsllm/backbones/<name>.py` with `@register_backbone(...)`; import the module in `backbones/__init__.py` | `tests/backbones/test_<name>*.py`; `pyproject.toml` if it needs a new library |
| Task type        | `src/tsllm/tasks/<type>.py` + `register_task(...)`                                    | Task config model in `config/run.py` (discriminated union on `type`)          |
| Metric           | `src/tsllm/evaluation/metrics.py`                                                     | `metrics.json` contract in the parent design §6.1                             |
| API route        | `src/tsllm/service/routes/<area>.py`                                                  | Response model in `service/models.py`; regenerate `web/openapi.json`          |
| CLI command      | `src/tsllm/cli.py`                                                                    | Nothing else                                                                  |
| Run template     | `configs/runs/<name>.yaml`                                                            | Nothing else                                                                  |

---

## Naming Conventions

- Modules and packages: `snake_case`. One adapter per module. The module name equals the registry key (`chronos2.py` → `"chronos2"`).
- Pydantic models: `PascalCase` nouns ending with the role: `DatasetConfig`, `RunConfig`, `BackboneConfig`, `FinetuneConfig`, `BackboneInfo`, `RunStatus`.
- Service response models end with `Out` (`RunDetailOut`). Request models end with `In`.
- Exceptions end with `Error` or describe the state: `CapabilityError`, `BackboneLoadError`, `DatasetNotIngested`, `InvalidTransition`.
- Channel names are the exact column names from the source file, including Chinese names. Do not translate or normalize them in code.
- Tests: `tests/<layer>/test_<module>.py`. Tests that need weights or a GPU end with `_weights.py` or `_gpu.py` and carry the matching pytest marker.

---

## Verified References

- CLI dispatch: `src/tsllm/__init__.py` and `src/tsllm/cli.py`; tests in `tests/test_cli.py`.
- Strict config models and duration parsing: `src/tsllm/config/base.py`, `src/tsllm/config/dataset.py`, `src/tsllm/config/labels.py`; tests in `tests/config/test_dataset.py`.
- Public data exports and containers: `src/tsllm/data/__init__.py` and `src/tsllm/data/types.py`.
- YAML-backed discovery: `src/tsllm/data/registry.py`; source parsing tests in `tests/data/test_source.py`.
- No model imports: `tests/data/test_stats_windows.py` checks the AST and imports the data package in an independent process.

## Adapter Implementation References

- Config: `src/tsllm/config/backbone.py`; configuration and schema tests in `tests/backbones/test_contract.py` and `test_registry.py`.
- Base contract and discovery: `src/tsllm/backbones/base.py`, `registry.py`, and `__init__.py`; isolated import assertions in `tests/backbones/test_contract.py`.
- Shared fit-window sampling, NaN treatment, and training: `src/tsllm/backbones/windows.py`, `nan.py`, and `training.py`; tests in `tests/backbones/test_baselines.py` and `test_training.py`.
- Adapter behavior: the six named modules in `backbones/`, with baseline and tiny-model tests under `tests/backbones/`. Real-checkpoint and CUDA acceptance are separate from offline checks.

Runner and service placement remains defined by the parent design §1–§2 and the matching child designs. Their listed paths are not implementation evidence.
