# Directory Structure

> How the Python package `src/tsllm` is organized.

---

## Overview

The project is one Python package, `tsllm`, in a `src/` layout. uv builds it with `uv_build`. The package has 7 layers. Dependencies go down only (see "Layer Rules").

Configuration files (YAML) live in `configs/`. Generated data lives in `cache/` and `runs/`. The web UI lives in `web/` (see `.trellis/spec/frontend/`).

---

## Directory Layout

```text
pyproject.toml
configs/
  datasets/<id>.yaml          # one DatasetConfig per file; file name == id
  runs/<name>.yaml            # RunConfig samples and templates
src/tsllm/
  __init__.py                 # main() calls cli.app()
  cli.py                      # typer entry point: data, run, runs, schema, serve, api
  errors.py                   # TsllmError base class
  reporting.py                # Reporter protocol and NullReporter
  config/                     # Pydantic models, YAML io, JSON Schema export
    base.py  io.py  dataset.py  backbone.py  run.py  schema.py
  data/                       # source read, resample, segments, splits, windows, labels, cache
    types.py  registry.py  source.py  rules.py  prepare.py  cache.py
    stats.py  windows.py  labels.py  profile.py
  backbones/                  # adapter protocol, registry, one module per adapter
    base.py  registry.py  checkpoint.py  windows.py  nan.py  training.py
    persistence.py  ridge.py  features.py  chronos2.py  timesfm25.py  ttm.py
  tasks/                      # task registry, forecast and classify pipelines
    registry.py  context.py  forecast.py  classify.py
  evaluation/                 # metrics and resource measurement
    metrics.py  resources.py
  runs/                       # run store, file reporter, env snapshot, worker entry
    store.py  reporter.py  env.py  seeding.py  worker.py
  service/                    # FastAPI app, job manager, SSE, routes
    app.py  settings.py  errors.py  models.py  jobs.py  sse.py  static.py
    routes/{system,schema,datasets,backbones,runs,compare,templates}.py
tests/                        # mirrors src/tsllm; fixtures make synthetic data
web/                          # React UI
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
| Backbone adapter | `src/tsllm/backbones/<name>.py` + one `register_backbone(...)` entry in `registry.py` | `tests/backbones/test_<name>*.py`; `pyproject.toml` if it needs a new library |
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

## Reference Examples

No implementation file exists yet. Use these design sections as the reference until the first child task lands:

- Layer and layout contract: `.trellis/tasks/09-28-tsfm-platform/design.md` §1–§2.
- Data module list: `.trellis/tasks/09-28-data-contract/design.md` §1.
- Adapter module list: `.trellis/tasks/09-28-backbone-adapters/design.md` §1.
- Runner module list: `.trellis/tasks/09-28-experiment-runner/design.md` §1.
- Service module list: `.trellis/tasks/09-28-service-api/design.md` §1.
