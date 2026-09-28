# FastAPI 服务与任务执行器

父任务：`.trellis/tasks/09-28-tsfm-platform/`。共享契约见父任务 `design.md` 第 1、6、7、8 节。

## 目标

提供网页所需的全部 HTTP 接口，并以子进程方式调度入库与实验作业。

## 依赖

- `09-28-experiment-runner` 已归档：使用 `RunStore`、`JobSpec`、`run_config_schema()`、worker 入口。

## 需求

- R1 依赖：`fastapi`、`uvicorn[standard]`、`psutil`；dev 组加入 `httpx`。
- R2 `create_app(settings)` 工厂；`Settings` 从环境变量 `TSLLM_RUNS_DIR`、`TSLLM_CACHE_DIR`、`TSLLM_CONFIGS_DIR`、`TSLLM_GPU_SLOTS`（默认 1）、`TSLLM_CPU_SLOTS`（默认 2）读取，默认值为仓库相对路径。
- R3 实现父设计第 7 节全部接口，所有请求与响应使用 Pydantic 模型，保证 OpenAPI 完整。
- R4 统一错误响应 `{"error": {"code", "message", "detail"}}`；Pydantic 校验错误映射为 422 + `code: "VALIDATION_ERROR"`；未入库映射为 409 + `DATASET_NOT_INGESTED`；运行不存在为 404 + `RUN_NOT_FOUND`。
- R5 作业执行器：两个资源池（gpu、cpu）；`device: cuda` 的实验进 gpu 池，其余进 cpu 池；FIFO；子进程命令 `[sys.executable, "-m", "tsllm.runs.worker", <run_dir>]`，命令可由 Settings 覆盖（供测试）。
- R6 取消：终止子进程树（psutil），写 `cancelled`；排队中的作业直接写 `cancelled`。
- R7 启动恢复：`running` 且 pid 不存在或不属于 worker 的作业写 `interrupted`；`queued` 作业按 `created_at` 重新入队。
- R8 SSE：`/api/runs/{id}/events` 从 `Last-Event-ID`（或查询参数 `from`）之后的行开始推送；每 15 s 发送注释心跳；作业进入终态且文件读完后发送 `event: end` 并关闭。
- R9 服务进程不导入 torch 与模型库（`/api/backbones` 使用注册表的无导入列表）。
- R10 `/api/datasets/{id}/series`：按 `max_points`（默认 2,000，上限 20,000）对时间范围做等间隔分桶，返回每桶均值；同时返回该范围内的段与划分边界。
- R11 `PUT /api/datasets/{id}/channels`：只允许修改 `role`、`unit`、`description`；通道名集合必须与原配置一致；写回 YAML 后响应中给出新的 `config_hash` 与 `needs_ingest`。
- R12 运行配置模板：`GET /api/run-templates`、`GET/PUT /api/run-templates/{name}`，名称限定 `[A-Za-z0-9_-]+`。
- R13 CLI：`tsllm serve [--host 127.0.0.1] [--port 8000]`；`tsllm api openapi --out <path>` 导出 OpenAPI JSON。
- R14 `web/dist` 存在时，服务在 `/` 下提供静态文件，未知非 `/api` 路径返回 `index.html`。
- R15 `/api/runs/{id}/predictions`：带 `origin_time` 时返回该起点的全部行（预测任务按 `channel` 过滤）；不带时返回该划分按时间排序的去重起点列表，按 `limit`（默认 500，上限 5,000）等间隔抽取。

## 验收标准

- [ ] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过。
- [ ] AC2 集成测试（TestClient + 真实子进程）：在合成数据集上提交入库作业与 persistence 实验，轮询到 `succeeded`，读取 metrics 与 predictions。
- [ ] AC3 取消测试：用 Settings 覆盖 worker 命令为长时间休眠的进程，取消后状态为 `cancelled`，进程不存在。
- [ ] AC4 恢复测试：预置 `running`（pid 不存在）与 `queued` 目录，启动后分别为 `interrupted` 与已入队。
- [ ] AC5 SSE 测试：读取到全部事件与 `end`；带 `Last-Event-ID` 时不重复发送已读事件。
- [ ] AC6 错误响应测试覆盖 404、409、422。
- [ ] AC7 测试断言服务启动与调用 `/api/backbones` 后 `sys.modules` 中无 `torch`。
- [ ] AC8 `uv run tsllm api openapi --out web/openapi.json` 生成的文件包含第 7 节全部路径。
