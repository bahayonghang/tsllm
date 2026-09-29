# 数据契约执行计划

开始条件：`00-bootstrap-guidelines` 已归档。

## 步骤

1. 工具链
   - `pyproject.toml`：加入依赖 polars、pyarrow、numpy、pydantic、pyyaml、typer；`[dependency-groups] dev = [ruff, pyright, pytest]`；`[tool.ruff]`、`[tool.pyright]`、`[tool.pytest.ini_options]`（含 `markers = gpu, weights`，默认 `-m "not gpu and not weights"`）。
   - `.gitignore` 加入 `runs/`、`cache/`。
   - `src/tsllm/__init__.py` 的 `main()` 调用 `tsllm.cli.app()`。
   - 验证：`uv sync`、`uv run tsllm --help`。
2. `tsllm.config`：`base.py`、`dataset.py`、`io.py`；测试 Duration 解析与 `extra="forbid"`。
3. `tsllm.data.source` + `registry`；测试类型声明、去重、编码、自动数值通道识别（含字符串标识列、前 N 行为空的数值列与全空列），以及显式非法数值通道的脱敏错误。
4. `prepare.py` 重采样与网格补齐；测试右端点标记与 `observed`。
5. `rules.py` + 分段 + 划分；测试 `max_gap`、`min_length`、划分比例。
6. `cache.py` + `profile.py`；测试哈希与过期判定。
7. `stats.py`、`windows.py`、`labels.py`；泄漏测试（AC2 列出的全部项）。
8. CLI `data list / ingest / profile`。
9. `configs/datasets/yangquan_kiln.yaml`、`configs/datasets/ETTh1.yaml`。
10. 真实数据验收：执行 AC4、AC5，把耗时、有效点数、段数、划分边界写入 `prd.md` 备注。

## 验证命令

```bash
uv sync
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest
uv run tsllm data ingest yangquan_kiln
uv run tsllm data profile yangquan_kiln
uv run tsllm data ingest ETTh1
```

## 审查门禁

- 步骤 7 完成后运行 `trellis-check`，重点检查泄漏测试是否能在删除对应约束后失败。
- 步骤 10 的数字与父任务 `research/data-profile.md` 偏差超过 2% 时，停止并在备注中写明原因再继续。

## 回滚点

- 步骤 1 独立可回退（只改工具链）。
- 步骤 2–9 为一个功能单元；验收失败时整体回退本子任务提交。
