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

- [ ] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过。
- [ ] AC2 合成数据端到端测试（CPU，无权重）：`persistence`、`ridge` 预测运行与 `features` 分类运行生成父设计第 6 节列出的全部文件，`metrics.json` 字段齐全。
- [ ] AC3 指标单元测试：MAE / RMSE / 归一化宏平均 / 分位数损失 / 覆盖率用手算小例子核对；分类指标与 sklearn 结果一致。
- [ ] AC4 同一任务配置、不同基座的两次运行，各划分 `origin_set_hash` 相同。
- [ ] AC5 worker 抛异常时 `status.json` 为 `failed`，事件流含堆栈；非法状态转换抛错。
- [ ] AC6 分类运行的 `label_info.json` 中阈值等于只用拟合段计算的分位数（测试中在测试段注入极端值验证）。
- [ ] AC7 在本机用 CLI 完成 R10 中水泥的 9 个运行；各运行的 test 划分主要指标、耗时、显存汇总成表写入任务备注。需要权重的运行在权重就绪后执行。
