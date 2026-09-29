# 实验运行器：预测与分类任务

父任务：`.trellis/tasks/09-28-tsfm-platform/`。共享契约见父任务 `design.md` 第 3.2、3.3、6、8 节。

## 目标

以 `RunConfig` 为唯一输入，在子进程或 CLI 中完成一次预测或分类运行，产出符合运行目录契约的全部文件。

## 依赖

- `09-28-data-contract`、`09-28-backbone-adapters` 已归档。

## 需求

- R1 `tsllm.config.run`：`ForecastTaskConfig`、`ClassifyTaskConfig`（按 `type` 判别）、`LabelRuleConfig`、`HeadConfig`、`RunConfig`、`JobSpec`。分类任务配置含 `max_train_origins`（默认 20,000，按时间均匀抽取，固定种子）。
- R2 `tsllm.config.schema`：`run_config_schema()` 返回 RunConfig schema 与各基座 Options schema（父设计 3.3）。
- R3 校验：`mode` 与基座能力匹配；`context_length`、`horizon` 不超过基座上限；`known_future_covariate` 通道报"未实现"；数据集未入库或缓存过期时报错（错误码 `DATASET_NOT_INGESTED`）。
- R4 预测任务：零样本与微调；按划分生成评价起点；批量预测；物理单位 MAE / RMSE（每通道、每提前量）；按拟合段标准差归一化的宏平均；有分位数输出时计算分位数损失、80% 区间（0.1 与 0.9 分位数）覆盖率与平均宽度。
- R5 分类任务：标签与阈值（父设计 3.2）；冻结表示；`StandardScaler` + `LogisticRegression` 或 `MLPClassifier`；在验证划分上选择使 F1 最大的判决阈值；输出 AUROC、AUPRC、F1、Brier、正类比例、混淆矩阵、ROC 与 PR 曲线。
- R6 资源指标：加载耗时、训练耗时、峰值显存（CUDA 时）、每批推理时延 p50 / p95（批大小写入 metrics）。
- R7 运行目录：`tsllm.runs.store` 负责创建、原子写入 `status.json`、追加 `events.jsonl`、列出与读取运行；状态转换只允许父设计第 6 节规定的写入方。
- R8 worker：`python -m tsllm.runs.worker <run_dir>`；设置随机种子；写环境快照；按 `JobSpec.kind` 执行入库或实验；未捕获异常写 `failed`，`status.error` 为一行摘要，完整堆栈写入事件流。
- R9 CLI：`tsllm run <config.yaml> [--ingest]`（前台执行，复用 worker 主函数）、`tsllm runs list`、`tsllm runs show <run_id>`、`tsllm schema`（打印 JSON Schema）。
- R10 样例配置 `configs/runs/`：水泥 7 个预测运行（保持值、岭回归、Chronos-2 零样本与 LoRA、TimesFM 2.5 零样本与 LoRA、TTM 零样本）、2 个分类运行（统计特征、Chronos-2 表示）、ETTh1 的保持值与 Chronos-2 零样本。水泥分类默认规则：`烟室NOX反馈` 在未来 30 步内连续 3 步高于拟合段 0.95 分位数。

## 验收标准

- [x] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过。
- [x] AC2 合成数据端到端测试（CPU，无权重）：`persistence`、`ridge` 预测运行与 `features` 分类运行生成父设计第 6 节列出的全部文件，`metrics.json` 字段齐全。
- [x] AC3 指标单元测试：MAE / RMSE / 归一化宏平均 / 分位数损失 / 覆盖率用手算小例子核对；分类指标与 sklearn 结果一致。
- [x] AC4 同一任务配置、不同基座的两次运行，各划分 `origin_set_hash` 相同。
- [x] AC5 worker 抛异常时 `status.json` 为 `failed`，事件流含堆栈；非法状态转换抛错。
- [x] AC6 分类运行的 `label_info.json` 中阈值等于只用拟合段计算的分位数（测试中在测试段注入极端值验证）。
- [x] AC7 在本机用 CLI 完成 R10 中水泥的 9 个运行；各运行的 test 划分主要指标、耗时、显存汇总成表写入任务备注。需要权重的运行在权重就绪后执行。

## 备注

### 实现偏差

- R1 写明 `max_train_origins` 抽样使用固定种子。实现改为 `np.linspace` 按时间均匀抽取，与 `max_eval_origins` 规则相同。结果是确定性的，不需要种子。`design.md` 第 6 节已同步。
- `origin_set_hash` 复用数据层 `tsllm.data.windows.origin_set_hash`（int64 微秒值的 SHA-256 前 12 位），不另写 ISO 字符串版本。`design.md` 第 5 节已同步。
- 新增 `tsllm.tasks.validation`（`validate_job`、`TaskConfigError`，错误码 `TASK_CONFIG_INVALID`），用于 R3 校验以及"划分无合法起点""训练标签只有一类"两种情况。

### AC1–AC6 离线证据

2026-09-29：`uv run ruff check`、`uv run ruff format --check`、`uv run pyright`（0 errors）通过；`uv run pytest` 146 passed、5 deselected。对应测试：`tests/runs/test_worker_e2e.py`（AC2、AC5）、`tests/evaluation/test_metrics.py`（AC3）、`tests/tasks/test_origin_hash.py`（AC4）、`tests/runs/test_store.py`（AC5 状态转换矩阵）、`tests/tasks/test_classify_leakage.py`（AC6）。

### AC7 本机 CLI 验收（2026-09-29）

环境：RTX 5090 Laptop，`HF_ENDPOINT=https://hf-mirror.com`。上下文 120、步长 30（预测）；test 划分预测起点 1,735 个，分类起点 5,204 个。9 个运行均为 `succeeded`。

预测运行（test 划分；`mae`/`rmse` 为拟合段标准差归一化的宏平均）：

| 运行 | run_id | mae_norm_macro | rmse_norm_macro | pinball | coverage_80 | 加载 s | 训练 s | 峰值显存 MiB | 时延 p50/p95 ms（批 64） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| persistence | 20260929-084253-kiln-persistence-e589 | 0.1909 | 0.3969 | — | — | 0.00 | — | — | 0.38 / 0.55 |
| ridge | 20260929-084259-kiln-ridge-9d63 | 0.2162 | 0.4164 | — | — | 0.00 | 1.53 | — | 5.3 / 9.9 |
| Chronos-2 零样本 | 20260929-082618-kiln-chronos2-zero-shot-8db1 | 0.1649 | 0.3647 | 0.0583 | 0.759 | 4.43 | — | 390 | 301 / 330 |
| Chronos-2 LoRA | 20260929-082825-kiln-chronos2-lora-fb72 | 0.1616 | 0.3583 | 0.0571 | 0.776 | 4.01 | 151.5 | 1554 | 366 / 395 |
| TimesFM 2.5 零样本 | 20260929-082710-kiln-timesfm25-zero-shot-b508 | 0.1726 | 0.3684 | 0.0694 | 0.680 | 4.34 | — | 771 | 377 / 421 |
| TimesFM 2.5 LoRA | 20260929-083129-kiln-timesfm25-lora-8452 | 0.1695 | 0.3625 | 0.0686 | 0.633 | 4.13 | 326.0 | 1244 | 468 / 561 |
| TTM 零样本 | 20260929-084336-kiln-ttm-zero-shot-c3ce | 0.1803 | 0.3774 | — | — | 0.00 | — | 36 | 20.7 / 26.2 |

分类运行（test 划分；规则：`烟室NOX反馈` 未来 30 步内连续 3 步高于拟合段 0.95 分位数；test 正类比例 0.116）：

| 运行 | run_id | AUROC | AUPRC | F1 | Brier | 判决阈值 | 训练 s | 峰值显存 MiB | 时延 p50/p95 ms（批 64） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 统计特征 | 20260929-084307-kiln-classify-features-a42f | 0.958 | 0.719 | 0.700 | 0.103 | 0.811 | 15.9 | — | 23.0 / 24.1 |
| Chronos-2 表示 | 20260929-083732-kiln-classify-chronos2-67ff | 0.752 | 0.280 | 0.349 | 0.157 | 0.00096 | 94.9 | 381 | 180 / 201 |

观察与说明：

- 各预测运行 test 划分 `origin_set_hash` 均为 `07c9ced03282`，分类运行均为 `024d71566f7f`，起点集合可比。
- 门禁：没有基础模型的 test 归一化 MAE 高于 persistence 的 2 倍；三个基础模型均低于 persistence（0.1909）。ridge 高于 persistence 13%，训练时 sklearn 报告病态矩阵警告（rcond 约 3.5e-8）。
- 解析到的 revision（见各运行 `env.json`）：Chronos-2 `29ec3766d36d6f73f0696f85560a422f50e8498c`，TimesFM 2.5 `5a9806b9b291fad9233b5249d88263f1846304d3`，TTM `6e5cb8ee51e0634a45637490f5db43148b2fa6be`（按 L=120、H=30 自动选择分支），许可均为 Apache-2.0。
- TTM 在首次 `forecast` 时才加载权重，因此加载耗时接近 0，加载时间计入首批时延。
- Chronos-2 表示分类明显弱于统计特征，验证集选出的判决阈值为 0.00096，说明逻辑回归头输出概率偏低。原因未查明；候选方向为高维拼接表示（`embed_channel_pool: concat`）下的过拟合或正则强度不足。本任务不调参。
- 统计特征运行每批报告一次"all-NaN context channels"警告，说明部分窗口存在整段缺失的通道；这是 `features` 适配器的既定行为。
- 首轮验收发现两处缺陷并已修复后复测：CPU 运行的 `peak_vram_mb` 为 0（应为 null）；TTM 的 `env.json` 缺少解析 revision（TTM 延迟解析检查点）。persistence、ridge、统计特征分类与 TTM 四个运行在修复后重跑，指标与首轮一致；表中为复测 run_id。
