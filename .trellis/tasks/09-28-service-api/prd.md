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

- [x] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过。
- [x] AC2 集成测试（TestClient + 真实子进程）：在合成数据集上提交入库作业与 persistence 实验，轮询到 `succeeded`，读取 metrics 与 predictions。
- [x] AC3 取消测试：用 Settings 覆盖 worker 命令为长时间休眠的进程，取消后状态为 `cancelled`，进程不存在。
- [x] AC4 恢复测试：预置 `running`（pid 不存在）与 `queued` 目录，启动后分别为 `interrupted` 与已入队。
- [x] AC5 SSE 测试：读取到全部事件与 `end`；带 `Last-Event-ID` 时不重复发送已读事件。
- [x] AC6 错误响应测试覆盖 404、409、422。
- [x] AC7 测试断言服务启动与调用 `/api/backbones` 后 `sys.modules` 中无 `torch`。
- [x] AC8 `uv run tsllm api openapi --out web/openapi.json` 生成的文件包含第 7 节全部路径。

## 备注

### 验收证据（2026-09-29，分支 `codex/service-api`）

| 验收项 | 证据 |
| --- | --- |
| AC1 | `uv run ruff check`：All checks passed；`uv run ruff format --check`：109 files already formatted；`uv run pyright`：0 errors；`uv run pytest`：165 passed，5 deselected（`gpu`/`weights` 标记），34.5 s。其中 `tests/service/` 19 项 |
| AC2 | `tests/service/test_api_jobs.py::test_ingest_and_persistence_run_succeed`：真实 worker 子进程执行入库作业与 persistence 实验，均为 `succeeded`；读取 metrics、起点列表（含 `limit` 抽取）、单起点全部行与按 `channel` 过滤的行；无 metrics 的入库作业返回 404 `RESULT_NOT_FOUND` |
| AC3 | `test_cancel_started_and_queued_jobs`：worker 命令替换为启动孙进程后休眠的进程；取消后状态为 `cancelled`，进程树中全部进程已结束；排队中（未启动）的作业直接写 `cancelled` 且之后不再启动；对已取消作业再次取消返回 409 `INVALID_TRANSITION` |
| AC4 | `test_restart_recovery`：预置 pid 已退出的 `running` 目录 → 启动后为 `interrupted`；预置 `queued` 实验 → 重新入队并执行到 `succeeded`；另预置 pid 存活且命令行含 `tsllm.runs.worker` 与该运行目录的 `running` 目录 → 保持 `running` 并重新挂接，进程被结束后服务写 `failed`（`worker exited with code unknown`） |
| AC5 | `tests/service/test_api_events.py`：终态运行收到全部 5 行事件（id 1–5，`event` 等于行的 `kind`）与 `end`；`Last-Event-ID: 3` 从 id 4 开始，`from=4` 从 id 5 开始；未写完换行的末行不发送；运行中追加的行与 15 s 心跳（测试中设为 0.1 s）均送达 |
| AC6 | `tests/service/test_api_basic.py::test_error_envelopes`：404（`RUN_NOT_FOUND`、`DATASET_NOT_FOUND`、`TEMPLATE_NOT_FOUND`、无路由 `NOT_FOUND`）、409（`DATASET_NOT_INGESTED`、`INVALID_TRANSITION`）、422（`VALIDATION_ERROR` 含字段路径、`CAPABILITY_UNSUPPORTED`、`BACKBONE_LOAD_FAILED`、`NOT_IMPLEMENTED`）；被拒绝的提交不创建运行目录 |
| AC7 | `test_service_does_not_import_model_libraries`：独立 Python 进程中启动应用并调用 `/api/backbones`、`/api/schema/run-config`、`/api/system`、`/api/runs`，之后 `torch`、`transformers`、`chronos`、`tsfm_public`、`peft`、`sklearn` 均不在 `sys.modules` |
| AC8 | `uv run tsllm api openapi --out web/openapi.json` 输出 `paths=18`；`test_openapi_has_design_paths` 断言应用 OpenAPI 与 CLI 导出文件的（方法, 路径）集合等于第 7 节 20 个操作，且错误响应引用 `ErrorOut` |

### 本机手动检查（implement.md 步骤 10）

- `uv run tsllm serve --port 8000`：`/api/health` 返回 `{"status":"ok"}`，`/docs` 返回 200。端口 8765 在本机被 Windows 保留端口范围占用（WinError 10013），与服务代码无关。
- `/api/datasets`：`yangquan_kiln`（`07c6f11007c2`）与 `ETTh1`（`b3ab93028b99`）均为 `fresh`。
- 经 `POST /api/runs` 提交水泥 persistence 运行 `20260929-092529-svc-kiln-persistence-948b`（上下文 120、步长 30，CPU），约 5 s 后 `succeeded`。
- `curl -N /api/runs/<id>/events`：收到 10 条事件（4 条 `stage`、6 条 `progress`）与 `event: end`（`succeeded`），事件数等于 `events.jsonl` 行数；`Last-Event-ID: 5` 从 id 6 开始。
- metrics：val 起点 1,728 个，test 起点 1,735 个，与 experiment-runner 本机验收一致；`/predictions?split=test` 返回 500 个起点，`total_origins` 1,735。
- `/api/system` 通过 nvidia-smi 读取 GPU：RTX 5090 Laptop，24,463 MiB；槽位 gpu 1、cpu 2。
- `/api/datasets/yangquan_kiln/series?max_points=2000`：1,999 个桶，桶宽 628 min，18 个通道，43 个段，响应 0.04 s。
- `/api/compare` 对单个运行返回 10 行指标，无警告。

### 与规划的偏差

- `TSLLM_CACHE_DIR`：worker 原先固定使用 `cache/datasets`。为使服务与 worker 使用同一缓存，`tsllm.data.cache.default_cache_root()` 改为读取该环境变量（未设置时仍为 `cache/datasets`），服务启动 worker 时设置该变量。CLI 同样受此变量影响。
- 路由的业务逻辑放在下层新模块：`tsllm.data.series`、`tsllm.data.channels`、`tsllm.config.templates`、`tsllm.runs.results`、`tsllm.runs.compare`；`tsllm.runs.env` 新增 `package_versions()` 与 `gpu_info()`（nvidia-smi，不导入 torch）。另增 `service/deps.py`（请求依赖）。
- 新增错误码：`CHANNEL_INVALID`（422）、`RESULT_NOT_FOUND`（404）、`NOT_IMPLEMENTED`（422，对应 `NotImplementedError`）、`NOT_FOUND`（无路由，404）、`HTTP_ERROR`（其他 HTTP 错误）。`TASK_CONFIG_INVALID` 与 `BACKBONE_LOAD_FAILED` 定为 422。映射已写入 `.trellis/spec/backend/error-handling.md`。
- 调度：每个池按槽位数启动同数量的调度协程，替代"队列 + 信号量"，行为等价（FIFO、并发上限等于槽位）。子进程用 `subprocess.Popen` 启动并轮询，未用 `asyncio.create_subprocess_exec`，使服务不依赖 Windows 事件循环类型。
- 竞争处理：服务侧全部状态写入持有同一把 `asyncio.Lock`；取消已启动的作业时先结束进程树，再写 `cancelled`，worker 已写终态则返回 409。
- `dump_yaml` 接受字典；`save_dataset` 写回数据集 YAML 时 `source.path` 统一为正斜杠。写回会去掉 YAML 注释。
- `PUT /channels` 对 `channels: null` 的数据集（例如 ETTh1）从新鲜缓存取通道列表并写出显式列表，因此 `config_hash` 改变，`needs_ingest` 为 true；缓存不新鲜时返回 `CHANNEL_INVALID`。
- 请求中的时间（`start`、`end`、`origin_time`）若带时区偏移，偏移被去掉而不换算，因为数据时间无时区。
- 状态表新增 `queued → failed`（写入者 service，2026-09-29 用户确认）：worker 未写入 `running` 就退出时，服务写 `failed`，`error = "worker exited with code N before it started"`。父设计第 6 节、`RunStore.ALLOWED_TRANSITIONS` 与 `error-handling.md` 已同步；测试 `test_worker_exit_before_running_is_failed`，`tests/runs/test_store.py::test_transition_matrix` 覆盖新组合。

### 遗留问题

- Windows 上 venv 的 `python.exe` 是启动器，会再启动基础解释器子进程；服务记录的进程 pid 与 `status.json` 中 worker 的 pid 不同，两者命令行相同。取消按进程树结束，恢复按命令行匹配，两种情况均已覆盖。
- Starlette 1.7 对 `httpx` 用于 TestClient 给出弃用警告（建议 `httpx2`）。本任务按 R1 使用 `httpx`，警告不影响测试结果。
- API 响应中的 `source.path` 在 Windows 上为反斜杠形式（`Path` 的 JSON 序列化），网页只显示该字段，不回写。
