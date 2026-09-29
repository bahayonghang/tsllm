# Storage Guidelines

> The project has no database. This file defines the file storage rules.

---

## Overview

Status: **Verified** for dataset YAML files and the prepared-data cache. Run directories and service config writes remain Decided.

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
- Implementations: `src/tsllm/config/io.py`, `src/tsllm/config/base.py`, and `src/tsllm/data/registry.py`. Registry loading suppresses YAML and Pydantic exception chains that can contain private values.

---

## Dataset Cache

- Path: `cache/datasets/<id>/<config_hash>/`. `config_hash` is the first 12 hex characters of SHA-256 over the canonical JSON of the fields that change the prepared data.
- `src/tsllm/data/cache.py::config_hash` excludes the dataset id and channel display metadata (`unit`, `description`). It preserves channel order and roles.
- `meta.json` stores the source file size and `mtime_ns`. `is_fresh(cfg)` compares the hash, the size, and `mtime_ns`. If one differs, the cache is stale.
- Stale or missing cache: raise `DatasetNotIngested`. Do not ingest implicitly inside a task. Ingest is a separate job.
- Use polars for all table work in `tsllm.data`. Use pandas only inside an adapter when the model library requires it.
- `src/tsllm/data/source.py::read_source` reads explicitly selected CSV channels with `pl.Float64`, and reads the timestamp as `pl.String` before configured parsing. Projection excludes ignored channels. This handles initially empty channels and numeric timestamp text.
- With `channels: null`, CSV discovery checks all non-null values in each column for Float64 conversion. It retains all-null columns and skips mixed or text columns. Parquet discovery uses numeric dtypes and retains all-null columns. Selected output channels are Float64.
- `write_cache` replaces temporary files with `os.replace`; `meta.json` is the completion marker and is replaced last. `ingest_dataset` compares the live source fingerprint before preparation, after preparation, and after cache writing. A post-write mismatch removes the marker and raises `DatasetConfigError`.

### Verified Scenario: Explicit Dataset Ingestion

#### 1. Scope / Trigger

The CLI, config registry, data preparation, and local cache share one ingestion boundary. Implementations are in `src/tsllm/cli.py`, `src/tsllm/data/registry.py`, `src/tsllm/data/prepare.py`, and `src/tsllm/data/cache.py`.

#### 2. Signatures

```python
ingest_dataset(
    cfg: DatasetConfig,
    reporter: Reporter,
    *,
    force: bool = False,
    cache_root: Path | None = None,
) -> PreparedFrame
```

CLI commands: `tsllm data list`, `tsllm data ingest <id> [--force]`, and `tsllm data profile <id>`.

#### 3. Contracts

- The registry resolves `configs/datasets/<id>.yaml`; `id` must match the filename. Config models reject unknown fields.
- Ingestion reuses a fresh cache unless `force=True`. `cache_root` overrides `cache/datasets` for isolated callers and tests. No environment variable is required.
- The return value is `PreparedFrame(frame, channels, freq, meta)` from `src/tsllm/data/types.py`. Metadata contains channel profiles, segments, split boundaries/counts, the config hash, and the source fingerprint.
- `profile` reads existing cache metadata. It must not create or repair a missing or stale cache.
- Source freshness uses size and `mtime_ns`; it does not prove content identity when both values remain unchanged.

#### 4. Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Unknown dataset id | `DatasetNotFound`, code `DATASET_NOT_FOUND` |
| Invalid YAML/config, filename mismatch, invalid source, or source change during ingestion | `DatasetConfigError`, code `DATASET_CONFIG_INVALID` |
| Missing, stale, or unreadable cache on read | `DatasetNotIngested`, code `DATASET_NOT_INGESTED` |
| Any domain error at the CLI | Exit 1 with the code and sanitized message |

Parser errors suppress raw exception chains. Post-write source changes invalidate the completion marker.

#### 5. Good/Base/Bad Cases

- Good: first ingestion prepares data and publishes the frame before the metadata marker.
- Base: a second ingestion reuses the fresh cache; `--force` prepares data again.
- Bad: the source changes during preparation or cache writing; ingestion fails and cache freshness must be false.

#### 6. Tests Required

- `tests/data/test_source.py`: late numeric values, automatic discovery, ignored columns, numeric timestamp text, and sanitized parser errors.
- `tests/data/test_cache.py`: round trip, display-only config changes, and source size/mtime/config expiration.
- `tests/data/test_ingest.py::test_ingest_reuses_cache_and_force_rebuilds`: preparation call counts and stage order.
- `tests/data/test_ingest.py::test_source_changes_cannot_produce_fresh_cache`: changes during preparation, before cache writing, and after cache writing must raise and leave no metadata marker.
- `tests/test_cli.py`: list/ingest/profile behavior, force rebuild, stale-cache refusal, and error privacy. All fixtures are synthetic.

#### 7. Wrong vs Correct

- Wrong: compare only the fingerprint saved in returned metadata after cache writing. A source change after metadata construction is missed.
- Correct: also read the live source fingerprint after `write_cache` returns, compare it to the initial fingerprint, and remove `meta.json` on mismatch. The implementation and regression are linked above.

---

## Run Directories (Planned)

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
