# Phase 3.4 提交方案

日期：2026-09-29。分支：`codex/backbone-adapters`。规划时 HEAD：`3bb3a92`。用户已于 2026-09-29 确认按本方案执行两组本地提交，并归档已完成的 backbone-adapters；不推送。

## 提交 1：依赖

`build(deps): 配置基座模型依赖与 CUDA 12.8 索引`

目的：安装 PRD R1 指定的模型库，锁定可在 Python 3.13 / sm_120 上执行的依赖组合。依赖变更单独成提交，不混入适配器实现。

- `pyproject.toml`
- `uv.lock`

## 提交 2：适配器、测试与契约证据

`feat(backbones): 实现六个适配器并完成本机验收`

目的：在既有数据契约下统一配置、注册、预测、微调和保存加载。包括经用户批准的 mode/Reporter 协议同步、全部回归测试、实际验收证据及 Phase 3.3 规范同步。

- `.trellis/spec/backend/directory-structure.md`
- `.trellis/spec/backend/error-handling.md`
- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/backend/model-adapter-guidelines.md`
- `.trellis/spec/backend/quality-guidelines.md`
- `.trellis/spec/backend/time-series-guidelines.md`
- `.trellis/tasks/09-28-backbone-adapters/check.jsonl`
- `.trellis/tasks/09-28-backbone-adapters/commit-plan.md`
- `.trellis/tasks/09-28-backbone-adapters/design.md`
- `.trellis/tasks/09-28-backbone-adapters/implement.jsonl`
- `.trellis/tasks/09-28-backbone-adapters/implement.md`
- `.trellis/tasks/09-28-backbone-adapters/prd.md`
- `.trellis/tasks/09-28-backbone-adapters/research/contract-adjustments.md`
- `.trellis/tasks/09-28-backbone-adapters/research/dependency-validation.md`
- `.trellis/tasks/09-28-backbone-adapters/research/final-review.md`
- `.trellis/tasks/09-28-backbone-adapters/research/implementation-evidence.md`
- `.trellis/tasks/09-28-backbone-adapters/research/library-api-audit.md`
- `.trellis/tasks/09-28-backbone-adapters/research/real-acceptance.md`
- `.trellis/tasks/09-28-backbone-adapters/research/step6-review.md`
- `.trellis/tasks/09-28-backbone-adapters/task.json`
- `.trellis/tasks/09-28-backbone-adapters/verification.md`
- `.trellis/tasks/09-28-experiment-runner/design.md`
- `.trellis/tasks/09-28-tsfm-platform/design.md`
- `AGENTS.md`
- `src/tsllm/backbones/__init__.py`
- `src/tsllm/backbones/base.py`
- `src/tsllm/backbones/checkpoint.py`
- `src/tsllm/backbones/chronos2.py`
- `src/tsllm/backbones/features.py`
- `src/tsllm/backbones/nan.py`
- `src/tsllm/backbones/persistence.py`
- `src/tsllm/backbones/registry.py`
- `src/tsllm/backbones/ridge.py`
- `src/tsllm/backbones/timesfm25.py`
- `src/tsllm/backbones/training.py`
- `src/tsllm/backbones/ttm.py`
- `src/tsllm/backbones/windows.py`
- `src/tsllm/config/__init__.py`
- `src/tsllm/config/backbone.py`
- `tests/backbones/__init__.py`
- `tests/backbones/conftest.py`
- `tests/backbones/test_baselines.py`
- `tests/backbones/test_chronos2_tiny.py`
- `tests/backbones/test_contract.py`
- `tests/backbones/test_cuda.py`
- `tests/backbones/test_registry.py`
- `tests/backbones/test_smoke_weights.py`
- `tests/backbones/test_timesfm25_tiny.py`
- `tests/backbones/test_training.py`
- `tests/backbones/test_ttm_tiny.py`
- `tests/data/test_stats_windows.py`

## 边界与确认

- 提交 2 依赖提交 1。完整撤回本任务时，先回退功能提交，再回退依赖提交。
- `experiment-runner/design.md` 只同步经批准的方法签名；未开始运行器、服务或界面实施。
- 初始工作区干净；当前候选均属于本任务，没有未识别的用户改动。执行前已再次核对状态，54 个候选文件与本清单一致；仅按明确路径暂存。
- `data/`、`ref/`、`runs/`、`cache/`、权重及 `*.log` 不在候选清单中；`.trellis/workspace/` 的既有跟踪保持不变。
- 最终全范围独立审查已通过；54 个候选文件与本方案一致。用户已确认两组提交及本任务归档；依赖提交已完成，功能提交随后执行。
- 用户本次确认已覆盖两组本地提交和 `task.py archive` 的自动提交；归档后记录工作日志。不推送，不归档父任务或其他未完成子任务。
