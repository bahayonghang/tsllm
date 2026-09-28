# 实验运行器设计

共享契约以父任务 `design.md` 第 3.2、3.3、6、8 节为准。

## 1. 模块

```text
src/tsllm/
  config/run.py             # 任务配置、RunConfig、JobSpec
  config/schema.py          # run_config_schema()
  tasks/
    __init__.py
    registry.py             # register_task、get_task；键为 task.type
    context.py              # TaskContext：run_dir、job、prepared、fit_stats、reporter、rng
    forecast.py             # run_forecast(ctx) -> dict（metrics）
    classify.py             # run_classify(ctx) -> dict
  evaluation/
    metrics.py              # forecast_metrics(...)、classification_metrics(...)
    resources.py            # Timer、peak_vram_mb()、latency_percentiles()
  runs/
    store.py                # RunStore
    reporter.py             # FileReporter(Reporter)
    env.py                  # environment_snapshot(backbone_info, resolved_checkpoint)
    seeding.py              # seed_everything(seed)
    worker.py               # main(run_dir) 与 __main__ 入口
```

## 2. RunStore

```python
class RunStore:
    def __init__(self, root: Path): ...
    def create(self, job: JobSpec) -> str                     # 返回 run_id，状态 queued
    def path(self, run_id: str) -> Path
    def read_status(self, run_id) -> RunStatus
    def transition(self, run_id, to: RunState, *, writer: Literal["worker", "service"], **fields) -> RunStatus
    def list(self) -> list[RunSummary]                        # 按 created_at 倒序
    def read_job(self, run_id) -> JobSpec
    def read_metrics(self, run_id) -> dict | None
```

- `transition` 检查允许的 (from, to, writer) 组合，不允许时抛 `InvalidTransition`。
- 原子写：写 `status.json.tmp` 后 `os.replace`。
- `RunSummary`：run_id、name、kind、dataset、task type、backbone、mode、state、created_at、finished_at、主要指标（test 划分 overall 中第一个指标）。

## 3. FileReporter

- 每次调用追加一行 JSON 并 `flush()`；字段 `ts`（ISO，UTC）、`kind`、其余负载。
- `progress` 事件限频：同一阶段两次写入间隔不少于 0.5 s，最后一步必写。
- 另提供 `stage(name)` 方法，写 `kind: stage` 事件（`load`、`finetune`、`evaluate:<split>`、`done`）。

## 4. 预测任务流程

1. `prepared = load_prepared(job.dataset)`；不新鲜时抛 `DatasetNotIngested`。
2. `fit_stats = compute_fit_stats(prepared)`，写 `fit_stats.json`。
3. 取目标通道（`role == target`）与过去协变量（`role == past_covariate`）。本轮适配器输入只含目标通道；存在 `past_covariate` 时报 `NotImplementedError("past covariates")`，并在 schema 描述中注明。
4. 校验能力；`backbone.load(cfg, fit_stats)`，计时。
5. `mode != zero_shot`：`segment_set(prepared, "fit", min_rows=L+H)`、`segment_set(prepared, "val", ...)`；`backbone.finetune(...)`；`save_adapter(run_dir/"adapter")`。
6. 对每个评价划分：`build_eval_manifest` → 按 `eval_batch_size`（默认 64）分批 → `context_batch` → `forecast` → 累积 → `targets`。
7. `forecast_metrics(y_true, mask, mean, quantiles, levels, fit_std, leads)`。
8. 写 `predictions/<split>.parquet` 与 `metrics.json`。

## 5. 指标定义

记 `e = y_pred - y_true`，只在 `mask` 为真处计算。

- 每通道：`mae_c = mean|e|`，`rmse_c = sqrt(mean e²)`，物理单位。
- 归一化宏平均：`mae_norm_macro = mean_c(mae_c / std_fit_c)`；`std_fit_c` 为 0 的通道排除并在 metrics 中列出。
- 每提前量 `k ∈ eval_leads`：只取第 k 步（1 起算）计算上述量。
- 分位数损失：对每个分位 `q`，`mean(max(q·(y-ŷ_q), (q-1)·(y-ŷ_q))) / std_fit_c`，再对通道与分位数取平均。
- 80% 区间：需要 0.1 与 0.9 分位数，`coverage_80 = mean(ŷ_0.1 ≤ y ≤ ŷ_0.9)`，`width_80 = mean_c(mean(ŷ_0.9 - ŷ_0.1) / std_fit_c)`；缺少任一分位数时两项为 null。
- `origin_set_hash`：对该划分起点时间（ISO 字符串，换行连接）求 SHA-256，取前 12 位。

分类：`auroc`（`roc_auc_score`）、`auprc`（`average_precision_score`）、`brier`（`brier_score_loss`）；判决阈值在验证划分上扫描 `precision_recall_curve` 的阈值，取 F1 最大者；该阈值用于所有划分的 `f1` 与 `confusion`。某划分只有一个类别时，`auroc` 与 `auprc` 为 null 并写入 `warnings`。

## 6. 分类任务流程

1. 同预测任务第 1–2 步。
2. `threshold = resolve_threshold(prepared, rule)`；训练与评价起点沿用父设计 4.3 的窗口规则，上下文长度为 L，目标长度 H 替换为标签窗口 W。
3. 训练起点超过 `max_train_origins` 时按时间均匀抽取。
4. `backbone.load`；对训练与各评价划分分批 `embed`（`embed_batch_size` 默认 64）。
5. `labels = future_event_labels(...)`；写 `label_info.json`（规则、阈值、各划分样本数与正类比例）。
6. 训练分类头；`joblib.dump` 到 `adapter/head.joblib`。
7. 验证划分选判决阈值；计算各划分指标与曲线；写 `predictions/<split>.parquet` 与 `metrics.json`。

## 7. 环境快照（`env.json`）

`python`、`platform`、`tsllm` 版本、`torch`（版本、CUDA 版本、`cuda_available`、GPU 名称、计算能力）、`transformers`、`peft`、`chronos-forecasting`、`granite-tsfm`、`polars`、`numpy`、`scikit-learn` 版本（未安装记 null）、基座 `checkpoint`、`resolved_revision`、`license`、`HF_ENDPOINT`（只记录是否设置及主机名）。

## 8. worker

```python
def main(run_dir: Path) -> int:
    store, run_id = RunStore(run_dir.parent), run_dir.name
    store.transition(run_id, "running", writer="worker", pid=os.getpid())
    reporter = FileReporter(run_dir / "events.jsonl")
    try:
        job = store.read_job(run_id)
        seed_everything(job.run.seed if job.run else 0)
        ...  # ingest 或 get_task(job.run.task.type)(ctx)
        store.transition(run_id, "succeeded", writer="worker")
        return 0
    except Exception as exc:
        reporter.log(traceback.format_exc(), level="error")
        store.transition(run_id, "failed", writer="worker", error=f"{type(exc).__name__}: {exc}")
        return 1
```

CLI `tsllm run` 调用 `store.create(job)` 后直接调用 `main(run_dir)`，与子进程共用同一代码路径。

## 9. 测试

| 文件                                   | 内容                                                     |
| -------------------------------------- | -------------------------------------------------------- |
| `tests/evaluation/test_metrics.py`     | 手算小例子；sklearn 一致性；单类别划分                   |
| `tests/runs/test_store.py`             | 创建、状态转换矩阵、原子写、列表排序                     |
| `tests/runs/test_worker_e2e.py`        | 合成数据集上 persistence、ridge、features 运行；失败路径 |
| `tests/tasks/test_origin_hash.py`      | 不同基座同一任务配置的起点哈希一致                       |
| `tests/tasks/test_classify_leakage.py` | 测试段注入极端值后阈值不变                               |
| `tests/config/test_schema.py`          | schema 可 JSON 序列化；判别联合；各基座 Options 均出现   |
