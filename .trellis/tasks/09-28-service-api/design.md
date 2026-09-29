# 服务设计

共享契约以父任务 `design.md` 第 1、6、7、8 节为准。

## 1. 模块

```text
src/tsllm/service/
  __init__.py
  app.py              # create_app(settings)；lifespan 启动 JobManager 与恢复
  settings.py         # Settings（Pydantic 模型，from_env()）
  errors.py           # ApiError、异常处理器、错误码常量
  models.py           # 请求 / 响应模型（RunSummaryOut、RunDetailOut、DatasetOut、SeriesOut、CompareOut ...）
  jobs.py             # JobManager
  sse.py              # tail_events(path, start_line, is_terminal) 异步生成器
  routes/
    system.py
    schema.py
    datasets.py
    backbones.py
    runs.py
    compare.py
    templates.py
  static.py           # web/dist 挂载与 SPA 回退
```

路由函数只做参数校验、调用下层函数和组装响应；业务逻辑位于 `tsllm.runs`、`tsllm.data`、`tsllm.config`。

## 2. JobManager

```python
class JobManager:
    def __init__(self, store: RunStore, settings: Settings): ...
    async def start(self) -> None          # 恢复 + 启动 gpu / cpu 两个调度循环
    async def stop(self) -> None           # 停止调度循环；不终止正在运行的子进程
    async def submit(self, job: JobSpec) -> str
    async def cancel(self, run_id: str) -> RunStatus
```

- 每个池一个 `asyncio.Queue` 与一个 `asyncio.Semaphore(slots)`。
- 调度循环：取 run_id → 若状态已为 `cancelled` 则跳过 → 获取信号量 → `asyncio.create_subprocess_exec(*cmd, cwd=repo_root, stdout/stderr → run_dir/worker.log)` → 等待结束 → 释放信号量。
- 子进程退出码非 0 且 `status.json` 仍为 `running`（worker 未能写入终态，例如被系统终止）时，服务写 `failed`，`error = "worker exited with code N"`。该转换已列入父设计第 6 节转换表。子进程已退出且状态仍为 `queued`（worker 未能写入 `running`）时，服务写 `queued → failed`，`error = "worker exited with code N before it started"`；该转换于 2026-09-29 经用户确认加入父设计第 6 节转换表。
- 取消：`psutil.Process(pid).children(recursive=True)` 与本进程一起 `terminate()`，3 s 后仍存活则 `kill()`。

## 3. 恢复判定

pid 存活且 `psutil.Process(pid).cmdline()` 含 `tsllm.runs.worker` 与该 run_dir 时视为仍在运行，重新挂接等待（轮询 pid 存活，结束后按第 2 节处理退出）；否则写 `interrupted`。

## 4. SSE

```text
id: <行号，从 1 开始>
event: <kind>
data: <该行 JSON>

```

- 读取位置从 `Last-Event-ID` 头或 `from` 查询参数的下一行开始。
- 每 0.5 s 检查文件新行；只发送以换行结尾的完整行。
- 每 15 s 无新事件时发送 `: ping`。
- 终态且无新行时发送 `event: end`，`data: {"state": ...}`。
- 使用 `StreamingResponse(media_type="text/event-stream")`，不引入额外依赖。

## 5. 对比

`/api/compare?run_ids=a,b,c`：

- 读取每个运行的 `config.yaml` 与 `metrics.json`。
- 返回 `columns`（运行信息）、`rows`（指标名 × 划分 × 运行值）、`warnings`（数据集不同、任务类型不同、`context_length` / `horizon` 不同、同一划分 `origin_set_hash` 不同、运行未成功）。

## 6. 数据集接口

- 列表：`list_datasets()` + `is_fresh()`；返回入库状态 `fresh | stale | missing`。
- 详情：配置 + `meta.json`（不新鲜时 meta 为 null）。
- series：用 polars 对 PreparedFrame 按时间范围过滤后 `group_by_dynamic(every=span/max_points)` 求均值。
- 修改通道：读取原 YAML 为 `DatasetConfig`，更新字段，`dump_yaml` 写回。

## 7. 测试辅助

- `tests/service/conftest.py`：临时目录下的 configs / runs / cache；合成数据集 YAML；`create_app(settings)`；`TestClient` 使用 lifespan。
- 等待作业完成的辅助函数：轮询 `/api/runs/{id}`，超时 60 s。
