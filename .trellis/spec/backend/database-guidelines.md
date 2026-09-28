# Storage Guidelines

> The project has no database. This file defines the file storage rules.

---

## Overview

All state is in files. There is no ORM, no SQL, and no migration tool. There are 3 storage areas:

| Area                                 | Format                                      | Writer                                              | Committed to git |
| ------------------------------------ | ------------------------------------------- | --------------------------------------------------- | ---------------- |
| `configs/datasets/`, `configs/runs/` | YAML                                        | User, service (`PUT` channels, `PUT` run-templates) | Yes              |
| `cache/datasets/<id>/<hash>/`        | `frame.parquet` + `meta.json`               | Ingest job                                          | No               |
| `runs/<run_id>/`                     | YAML, JSON, JSONL, Parquet, adapter weights | service (create, cancel), worker (everything else)  | No               |

Raw data in `data/` and the research pack in `ref/` are read-only inputs. Never write to them. Never commit them.

---

## Config Files (YAML)

- Read with `tsllm.config.io.load_yaml(Model, path)`. Write with `dump_yaml(model, path)`. Do not call `yaml.safe_load` in other modules.
- All config models inherit `StrictModel` (`extra="forbid"`). An unknown key is an error.
- A dataset file name must equal its `id` (`configs/datasets/yangquan_kiln.yaml` → `id: yangquan_kiln`).
- Always open files with `encoding="utf-8"`. Channel names contain Chinese characters. The Windows default encoding (GBK) breaks them.

---

## Dataset Cache

- Path: `cache/datasets/<id>/<config_hash>/`. `config_hash` is the first 12 hex characters of SHA-256 over the canonical JSON of the fields that change the prepared data.
- `meta.json` stores the source file size and `mtime_ns`. `is_fresh(cfg)` compares the hash, the size, and `mtime_ns`. If one differs, the cache is stale.
- Stale or missing cache: raise `DatasetNotIngested`. Do not ingest implicitly inside a task. Ingest is a separate job.
- Use polars for all table work in `tsllm.data`. Use pandas only inside an adapter when the model library requires it.
- Read CSV with explicit `schema_overrides` for every channel (`pl.Float64`). Polars infers some channels as `String` because the first rows are empty.

```python
# Reference pattern (data-contract design §2)
frame = pl.read_csv(
    path,
    schema_overrides={ch: pl.Float64 for ch in channels},
    try_parse_dates=False,
    encoding=cfg.source.encoding,
)
```

---

## Run Directories

- One directory per job: `runs/<YYYYmmdd-HHMMSS>-<slug>-<4 random chars>/`. The layout is in the parent design §6.
- `status.json` changes only through `RunStore.transition(run_id, to, writer=...)`. The allowed transitions and writers are in the parent design §6 table. Do not write `status.json` directly.
- Atomic write for every JSON file that another process reads (`status.json`, `metrics.json`): write `<name>.tmp`, then `os.replace`.
- `events.jsonl` is append-only. Write one complete line per event, then call `flush()`. Readers send only lines that end with `\n`.
- `config.yaml` in a run directory is a snapshot (`JobSpec`). Never change it after the job is created.
- Predictions are long-format Parquet (`origin_time, channel, lead, y_true, y_pred, q_<level>...`).

---

## Forbidden Patterns

| Pattern                                            | Reason                                          |
| -------------------------------------------------- | ----------------------------------------------- |
| A SQLite file or other database for run state      | The run directory is the single source of truth |
| Write into `data/` or `ref/`                       | Raw inputs are read-only and are not in git     |
| `open(path)` without `encoding="utf-8"`            | Chinese channel names break on Windows          |
| Change `status.json` without `RunStore.transition` | The state machine rules are lost                |
| Cache key from the file path only                  | A config change must make a new cache directory |
