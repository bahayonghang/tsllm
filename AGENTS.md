# tsllm

A platform for time-series foundation model (TSFM) experiments. It runs zero-shot forecasting, LoRA fine-tuning, and representation-based classification on different backbones with one data contract and one evaluator. A web UI configures runs, shows live progress, and compares results.

The first dataset is the Yangquan rotary kiln DCS data (`data/阳泉回转窑联合训练孪生样本/data_in.csv`, 18 channels, 10 s sampling, 2023-01-01 to 2025-05-21). The research basis is `ref/cement_tsfm_research_20260928/`.

## Status

- Data-contract implementation and AC1–AC6 validation are complete. Its six applicable backend guides are Verified for the implemented scope. The implementation is committed as `04bd695`. Completion evidence is retained with the data-contract task under `.trellis/tasks/archive/`.
- Backbone-adapters implementation and local checkpoint/CUDA acceptance are complete on `codex/backbone-adapters`. Its task retains failure and rerun evidence. Final full-scope review passed. Evidence is retained in `.trellis/tasks/archive/2026-09/09-28-backbone-adapters/verification.md`.
- Experiment-runner implementation and local acceptance are complete (`65b6f11`).
- Service-api implementation and local acceptance are complete (`212ccf2`). The state table includes `queued → failed` (service).
- Web-ui implementation and in-app browser acceptance (AC1–AC6) are complete (`2b26ac4`). The frontend guides are Verified. Parent integration review also checked visible chart canvases and verified the comparison-chart legend fix. Evidence is in the parent task `prd.md`.
- All five child tasks and the parent task are archived under `.trellis/tasks/archive/2026-09/`. Parent integration acceptance (AC1–AC7) is complete and recorded in the parent task `prd.md`. AC1 covers the user-approved process-level offline environment; whole-machine network isolation was not tested.
- Archived parent task: `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/`. Read its `prd.md` and `design.md` before any work. `design.md` holds the shared contracts.
- Child tasks, in order: `09-28-data-contract` → `09-28-backbone-adapters` → `09-28-experiment-runner` → `09-28-service-api` → `09-28-web-ui`. Each child has `prd.md`, `design.md`, `implement.md`.

## Stack

- Python 3.13, uv, `src/tsllm` package. polars + Parquet, Pydantic v2 + YAML, typer CLI, FastAPI (REST + SSE), pytest, ruff, pyright.
- Models: torch 2.11 (CUDA 12.8 build), transformers 5.x, peft, chronos-forecasting 2.x, granite-tsfm 0.3.x.
- Web: `web/`, Vite + React 19 + TypeScript 5.9 + antd 6 + ECharts, pnpm, Biome, Vitest.
- GPU: RTX 5090 Laptop (sm_120, 24,463 MiB).

## Commands

All child tasks have landed. These commands work.

```bash
uv sync
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest                                   # offline; no weights, no GPU, no data/
HF_ENDPOINT=https://hf-mirror.com uv run pytest -m "gpu or weights"
uv run tsllm data ingest yangquan_kiln
uv run tsllm run configs/runs/<name>.yaml
uv run tsllm serve --port 8000
pnpm -C web run check
pnpm -C web run test
pnpm -C web run build
```

## Rules

- Never commit `data/`, `ref/`, `runs/`, or `cache/`. Never copy raw data values, the research report, or thesis text into code, tests, logs, commits, or published pages.
- The platform is offline analysis only. It never writes to a plant control system.
- Leakage rules are mandatory: chronological splits only; statistics and label thresholds from fit rows only; windows stay inside one segment; training targets stay inside the fit split. See `.trellis/spec/backend/time-series-guidelines.md`.
- A new dataset is one YAML file in `configs/datasets/`. A new backbone is one adapter module plus one registry entry. Tasks, service, and web code must not contain dataset ids, channel names, or backbone names.
- The service process does not import torch. Model libraries are imported only inside adapter methods.
- `huggingface.co` is not reachable from this machine. Use `HF_ENDPOINT=https://hf-mirror.com` or a local checkpoint directory. Record the resolved revision.
- Do not add TimesFM-3 (license does not allow this use). Do not add `momentfm` to the main environment (it pins transformers 4.33 and numpy 1.25).
- Open text files with `encoding="utf-8"`. Channel names are Chinese and must stay exact.

## Language

- Code, comments, and `.trellis/spec/` files: English.
- `.trellis/tasks/` planning files and web UI text: Chinese.

## Where to Read

| Need | File |
| --- | --- |
| Requirements and acceptance | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md` |
| Shared contracts (config, data, adapter, run directory, API) | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md` |
| Data facts | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/research/data-profile.md` |
| Library versions and APIs | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/research/library-compatibility.md` |
| Which report clauses apply | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/research/report-applicability.md` |
| Backend conventions | `.trellis/spec/backend/index.md` |
| Frontend conventions | `.trellis/spec/frontend/index.md` |

<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
