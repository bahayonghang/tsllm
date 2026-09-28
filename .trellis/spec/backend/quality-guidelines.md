# Quality Guidelines

> Tools, test rules, and review standards for `src/tsllm`.

---

## Toolchain

| Tool    | Use                                              | Command                                           |
| ------- | ------------------------------------------------ | ------------------------------------------------- |
| uv      | Python 3.13 environment, dependencies, lock file | `uv sync`, `uv add <pkg>`, `uv add --dev <pkg>`   |
| ruff    | Lint and format                                  | `uv run ruff check`, `uv run ruff format --check` |
| pyright | Type check                                       | `uv run pyright`                                  |
| pytest  | Tests                                            | `uv run pytest`                                   |

A change is complete only when all 4 commands pass.

Configuration in `pyproject.toml` (set by the data-contract child):

```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
# Chinese text in strings and comments uses full-width punctuation.
ignore = ["RUF001", "RUF002", "RUF003"]

[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.13"
typeCheckingMode = "standard"
reportMissingTypeStubs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not gpu and not weights'"
markers = [
  "gpu: needs a CUDA GPU",
  "weights: downloads or reads real model weights",
]
```

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
- Adapter tests without weights build tiny random models from a config (TimesFM 2.5, TTM). Tests with real weights carry `@pytest.mark.weights`. Tests that need CUDA carry `@pytest.mark.gpu`.
- Run the marked tests on a machine with weights: `HF_ENDPOINT=https://hf-mirror.com uv run pytest -m "gpu or weights"`.
- The service tests use `fastapi.testclient.TestClient` and a real worker subprocess for the `persistence` backbone.
- Assert numbers with a stated tolerance: `np.testing.assert_allclose(actual, expected, rtol=1e-6)`.

### Required leakage tests

Every change in `tsllm.data`, `tsllm.tasks`, or an adapter `finetune` must keep these tests green (parent AC7):

1. No training target row is after the last fit row.
2. `FitStats` does not change when you add extreme values to the val, cal, or test rows.
3. The label threshold does not change when you add extreme values outside the fit rows.
4. No window crosses a segment boundary.
5. The evaluation origin set (`origin_set_hash`) is the same for 2 backbones with the same task config.

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
