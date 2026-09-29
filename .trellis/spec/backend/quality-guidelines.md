# Quality Guidelines

> Tools, test rules, and review standards for `src/tsllm`.

---

## Toolchain

Status: **Verified** for the data-contract and backbone-adapters implementations, offline synthetic/tiny-model tests, and local real-checkpoint/CUDA acceptance. Evidence is in `.trellis/tasks/archive/2026-09/09-28-data-contract/verification.md` and `.trellis/tasks/archive/2026-09/09-28-backbone-adapters/verification.md`. The experiment runner is Verified by the offline tests listed below and by local CLI acceptance recorded in `.trellis/tasks/09-28-experiment-runner/prd.md`. Service requirements remain planned.

| Tool    | Use                                              | Command                                           |
| ------- | ------------------------------------------------ | ------------------------------------------------- |
| uv      | Python 3.13 environment, dependencies, lock file | `uv sync`, `uv add <pkg>`, `uv add --dev <pkg>`   |
| ruff    | Lint and format                                  | `uv run ruff check`, `uv run ruff format --check` |
| pyright | Type check                                       | `uv run pyright`                                  |
| pytest  | Tests                                            | `uv run pytest`                                   |

A change is complete only when all 4 commands pass.

The active configuration is in `pyproject.toml`; resolved dependency versions are in `uv.lock`.

- Ruff targets Python 3.13, uses a 100-column line length, and selects `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, and `RUF`. `RUF001`–`RUF003` allow exact Chinese text.
- Ruff excludes `.trellis` generated tools and planning files through `extend-exclude`. The application and test rules remain enabled. Check discovery with `uv run ruff check --show-files` when changing ignore rules.
- Pyright checks `src` and `tests` in standard mode for Python 3.13. Missing third-party type stubs are not reported.
- Pytest collects `tests` and excludes the registered `gpu` and `weights` markers by default.
- `.gitignore` uses root-anchored `/data/`, `/ref/`, `/runs/`, and `/cache/`. An unanchored `data/` also hides `src/tsllm/data` and `tests/data` from Git and Ruff discovery. Source and test directories must remain visible.

- Add dependencies with `uv add`. Do not edit `uv.lock` by hand.
- torch comes from the `pytorch-cu128` index (backbone-adapters implement step 1). The GPU is sm_120. Do not install a CPU-only torch or a CUDA build older than 12.8.
- Do not add `momentfm`. It pins `transformers` 4.33 and `numpy` 1.25 and breaks the environment.

---

## Code Rules

- Type hints on every public function, method, and dataclass field. Use `X | None`, not `Optional[X]`.
- Config and API models are Pydantic v2 models. Config models inherit `StrictModel` (`extra="forbid"`).
- Internal array containers are frozen dataclasses (`PreparedFrame`, `ContextBatch`, `SegmentSet`). Document array shapes in the field comment: `values: np.ndarray  # (B, C, L) float32`.
- Import heavy libraries (`torch`, `transformers`, `chronos`, `tsfm_public`, `peft`, `sklearn`) inside the function that uses them, in `tsllm.backbones` and `tsllm.tasks` only. Use `if TYPE_CHECKING:` imports for type hints.
- Pass a seeded `np.random.Generator` into functions that sample. Do not call `np.random.seed` or the global `random` module.
- Paths are `pathlib.Path`. Open text files with `encoding="utf-8"`.
- Comments explain why. Do not restate the code.

---

## Test Rules

- Tests run offline. The default `uv run pytest` must not download weights, must not need a GPU, and must not read `data/`.
- Use synthetic fixtures from `tests/conftest.py` (a small multichannel series with known running segments, gaps, and duplicate timestamps).
- `tests/data/test_stats_windows.py` uses AST checks and an independent Python process to verify that importing `tsllm.data` does not import model libraries. An already-imported test process alone is insufficient evidence.
- `tests/data/test_source.py`, `tests/data/test_ingest.py`, and `tests/test_cli.py` use temporary files for source errors, cache changes, and CLI privacy. Local real-data acceptance runs separately and records only aggregate counts, timings, and time metadata.
- Adapter tests without weights build tiny random models from the installed library config classes (Chronos-2, TimesFM 2.5, TTM), save them in a temporary directory, and use CPU fp32. `tests/backbones/test_*_tiny.py` covers shape, NaN handling, loss reduction, and adapter round trips. Tests with real weights carry `@pytest.mark.weights`. Tests that need CUDA carry `@pytest.mark.gpu`.
- Run the marked tests on a machine with weights: `HF_ENDPOINT=https://hf-mirror.com uv run pytest -m "gpu or weights"`.
- The marked tests in `tests/backbones/test_smoke_weights.py` and `test_cuda.py` do not skip missing checkpoints or hardware. Record failed attempts separately from corrected reruns. LoRA acceptance requires `0 < trainable_params < 0.05 * total_params`; TTM uses head training.
- `tests/backbones/test_contract.py::test_registry_import_is_light` imports and lists all six adapters in a fresh Python process, then checks that torch, chronos, transformers, tsfm_public, peft, and sklearn remain absent from `sys.modules`. A parent pytest process can already contain libraries used by tiny-model tests.
- The service tests use `fastapi.testclient.TestClient` and a real worker subprocess for the `persistence` backbone.
- Assert numbers with a stated tolerance: `np.testing.assert_allclose(actual, expected, rtol=1e-6)`.

### Required leakage tests

Every change in `tsllm.data`, `tsllm.tasks`, or an adapter `finetune` must keep these tests green (parent AC7):

1. No training target row is after the last fit row.
2. `FitStats` does not change when you add extreme values to the val, cal, or test rows.
3. The label threshold does not change when you add extreme values outside the fit rows.
4. No window crosses a segment boundary.
5. The evaluation origin set (`origin_set_hash`) is the same for 2 backbones with the same task config.

Current evidence: `tests/data/test_stats_windows.py` covers fit-only statistics, masks, legal manifests, extraction boundaries, and deterministic origin hashes. `tests/data/test_labels.py` covers fit-only thresholds and exact future-window endpoints. Both test files exclude ineligible fit rows from statistics and thresholds. `tests/tasks/test_origin_hash.py` covers cross-backbone origin sets (item 5). `tests/tasks/test_classify_leakage.py` covers the end-to-end label threshold (item 3).

Adapter evidence: `tests/backbones/test_baselines.py::test_windows_never_cross_arrays` checks seeded sampling, legal context/target endpoints, and insufficient-length rejection in `src/tsllm/backbones/windows.py`. `tests/backbones/test_training.py` checks fixed validation samples and restoration of the lowest-loss trainable weights. The data layer remains responsible for clipping `SegmentSet` arrays to the fit split before training.

An isolated mutation check must fail through a relevant assertion or missing expected exception. Import, syntax, and setup failures do not prove that a leakage test detects the removed constraint. The eight checks for this task are recorded in `.trellis/tasks/archive/2026-09/09-28-data-contract/verification.md`.

---

## Forbidden Patterns

| Pattern                                                              | Reason                                                                 |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `import torch` at module top level outside an adapter method         | The service and the data layer must import without torch               |
| A random train/test split, or `shuffle=True` across split boundaries | Leaks future data into training                                        |
| Statistics or thresholds from all rows                               | Leaks val and test data; use fit rows only                             |
| Hard-coded channel names or dataset ids in code                      | Datasets are config. Channel names belong in `configs/datasets/*.yaml` |
| Hard-coded backbone names in tasks, service, or web                  | Use the registry and capabilities                                      |
| Tests that read `data/` or `ref/`                                    | Those folders are not in git and tests must run anywhere               |
| Silent fallback to another mode or model                             | Results must match the config that the user submitted                  |

---

## Review Checklist

- [ ] The 4 toolchain commands pass.
- [ ] Layer rules in `directory-structure.md` hold (check imports).
- [ ] New config fields appear in the JSON Schema and have a `description`.
- [ ] New metrics or files in the run directory are in the parent design §6.
- [ ] Leakage tests pass and cover the new code path.
- [ ] No data values, secrets, or `ref/` text in logs, errors, tests, or commits.
