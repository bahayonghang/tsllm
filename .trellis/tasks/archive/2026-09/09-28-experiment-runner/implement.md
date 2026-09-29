# 实验运行器执行计划

开始条件：`09-28-data-contract`、`09-28-backbone-adapters` 已归档。

## 步骤

1. `config/run.py`、`config/schema.py`；schema 测试。
2. `evaluation/metrics.py`、`resources.py`；指标测试。
3. `runs/store.py`、`reporter.py`、`seeding.py`、`env.py`；存储与状态转换测试。
4. `tasks/registry.py`、`context.py`、`forecast.py`；persistence 与 ridge 端到端测试。
5. `tasks/classify.py`；features 端到端测试与泄漏测试。
6. `runs/worker.py`；失败路径测试。
7. CLI：`run`、`runs list`、`runs show`、`schema`。
8. `configs/runs/` 样例配置（R10）。
9. 本机执行 AC7：先运行 CPU 基线（persistence、ridge、features），再在权重就绪后运行其余 6 个；汇总表写入 `prd.md` 备注。

## 验证命令

```bash
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest
uv run tsllm run configs/runs/kiln_persistence.yaml
uv run tsllm run configs/runs/kiln_classify_features.yaml
uv run tsllm runs list
```

## 审查门禁

- 步骤 5 完成后运行 `trellis-check`，检查任务层没有绕过 `tsllm.data` 直接读取 PreparedFrame 列。
- 步骤 9 中任一基础模型运行的 test 归一化 MAE 高于 persistence 的 2 倍时，先检查单位、通道顺序、NaN 处理和时间对齐（报告 6.1 节），结论写入备注后再继续。

## 回滚点

- 步骤 1–3 为基础设施，可独立提交。
- 步骤 4–8 为功能单元；验收失败时回退该部分提交。
