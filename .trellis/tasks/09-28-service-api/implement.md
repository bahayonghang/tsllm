# 服务执行计划

开始条件：`09-28-experiment-runner` 已归档。

## 步骤

1. 依赖：fastapi、uvicorn[standard]、psutil；dev 组 httpx。
2. `settings.py`、`errors.py`、`models.py`、`app.py` 骨架与 `/api/health`、`/api/system`；错误处理测试。
3. `routes/schema.py`、`backbones.py`、`templates.py`。
4. `routes/datasets.py`（列表、详情、series、通道修改、入库提交）。
5. `jobs.py` + `routes/runs.py`（提交、列表、详情、取消、metrics、predictions）；集成、取消、恢复测试。
6. `sse.py` + events 路由；SSE 测试。
7. `routes/compare.py`。
8. `static.py`。
9. CLI `serve` 与 `api openapi`；导出 `web/openapi.json`。
10. 本机手动检查：`uv run tsllm serve` 后访问 `http://127.0.0.1:8000/docs`，提交一个 persistence 运行并通过 `curl -N` 读取 SSE。

## 验证命令

```bash
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest
uv run tsllm api openapi --out web/openapi.json
uv run tsllm serve --port 8000
```

## 审查门禁

- 步骤 5 完成后运行 `trellis-check`，重点检查路由中没有业务逻辑、状态写入都经过 `RunStore.transition`。

## 回滚点

- 步骤 1–9 为一个功能单元；回滚时删除 `src/tsllm/service/`、`tests/service/` 与新增依赖。
