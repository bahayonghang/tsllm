# 阳泉回转窑时序预测

## 目标

在已经验收的数据契约和评价器上，对阳泉回转窑 18 个 DCS 通道做同一窗口下的离线多步预测，并留下可以互相比较的运行记录。

本任务执行现有配置。不新增基座，不改变预测语义。

## 背景

- 数据集配置：`configs/datasets/yangquan_kiln.yaml`。源文件是 `data/阳泉回转窑联合训练孪生样本/data_in.csv`。
- 预测配置：`configs/runs/kiln_persistence.yaml`、`kiln_ridge.yaml`、`kiln_chronos2_zero_shot.yaml`、`kiln_chronos2_lora.yaml`、`kiln_timesfm25_zero_shot.yaml`、`kiln_timesfm25_lora.yaml`、`kiln_ttm_zero_shot.yaml`。
- 数据画像与历史窗口计数见归档 `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/research/data-profile.md` 和该目录 `prd.md` 的 AC3。当前工作区没有那些历史 `runs/` 目录，需要重跑。
- 本任务的实验契约说明在 `research/forecast-contract.md`。

## 已确认决策

| 编号 | 决策 |
| --- | --- |
| D1 | 使用现有 `yangquan_kiln` 配置。18 个通道都是 `target`。不把通道改成协变量，也不把通道标成 `ignore`。 |
| D2 | 七个预测运行使用仓库里的现有 YAML。上下文 120 步、预测长度 30 步、评价提前量 5/15/30、评价起点步长 30、评价划分 val 与 test。 |
| D3 | 模型取舍只看 val。test 只作为最后一次核对，不参与选型。 |
| D4 | 需要权重时使用 `HF_ENDPOINT=https://hf-mirror.com` 或本地已缓存检查点。Chronos-2 与 TimesFM 2.5 保持 YAML 中的 revision。TTM 的 `revision: null` 保持不变，由适配器解析并写入运行目录。 |
| D5 | 只做离线实验。不向窑控制系统写入任何值。 |
| D6 | 不纳入 TimesFM-3。不打开 Chronos-2 的 `cross_learning`。不实现未来已知协变量或过去协变量。 |
| D7 | 分类配置 `kiln_classify_chronos2.yaml` 与 `kiln_classify_features.yaml` 不在本任务范围。 |

## 需求

- R1 按当前数据集 YAML 入库 `yangquan_kiln`。缓存必须与该 YAML 一致。
- R2 按 `implement.md` 的顺序完成七个预测运行：保持值、岭回归、Chronos-2 零样本、TimesFM 2.5 零样本、TTM 零样本、Chronos-2 LoRA、TimesFM 2.5 LoRA。
- R3 七个成功运行在同一划分上的 `origin_set_hash` 必须相同。
- R4 每个成功运行都有 `metrics.json`，以及 `predictions/val.parquet` 和 `predictions/test.parquet`。
- R5 在本任务 `research/comparison.md` 记录每个运行的 `run_id`、状态、检查点 revision、val/test 的 `mae_norm_macro`、`rmse_norm_macro`、`n_origins`、`origin_set_hash` 和资源指标。按 val 的 `mae_norm_macro` 从小到大排序，并写明 test 未用于选型。
- R6 环境失败（缺数据、缺权重、无 GPU、进程失败）要保留运行目录和错误摘要。不得通过修改窗口、划分或有效性规则让运行“通过”。
- R7 默认不改产品代码。只有既有缺陷阻断 R2 时才做最小修复，并把缺陷、修复和复跑结果写进 `research/`。

## 约束

- C1 沿用平台约束：Python 3.13、uv、RTX 5090 使用 CUDA 12.8 及以上的 torch。`huggingface.co` 直连不可用。
- C2 `data/`、`cache/`、`runs/` 不入库。可入库的结果只放在本任务目录的 `research/`。
- C3 拟合段统计、LoRA 训练目标和标签阈值只用 fit 段。评价窗口不得跨连续段，目标不得跨划分。
- C4 单元测试不得依赖网络和真实权重。本任务的真实权重运行是本地验收，不写入默认 `pytest`。

## 不在本任务范围

- 修改 Chronos-2 推理的 `cross_learning`。
- 实现 `past_covariate` 或 `known_future_covariate`。
- 只预测单个通道，或把其余通道留在上下文里。
- 烟室 NOX 事件分类。
- 新基座、网页改动、把预测写回 DCS。

## 验收标准

- [x] AC1 `uv run tsllm data profile yangquan_kiln` 打印数据集 id、频率、行数、有效点数、段数和四个划分边界。`research/ingest.md` 记录源文件字节数、缓存哈希，以及与归档基准 523,702 个有效分钟的偏差。偏差超过 ±2% 时写明源文件指纹，不得改有效性规则去消除偏差。
- [x] AC2 七个预测运行的状态都是 `succeeded`，`error` 为空。
- [x] AC3 七个运行的 val `origin_set_hash` 相同，test `origin_set_hash` 相同。源文件字节数仍为 1,068,005,224 时，这两个哈希必须等于归档值 `e51e301e6b09` 和 `07c9ced03282`。字节数不同时，在 `research/comparison.md` 写明新指纹和新哈希，不得静默改窗口去凑旧哈希。
- [x] AC4 `research/comparison.md` 包含七行结果、val 排序，以及“test 未用于选型”的说明。
- [x] AC5 六个需要权重的运行在 `env.json` 记录解析后的 revision。Chronos-2 为 `29ec3766d36d6f73f0696f85560a422f50e8498c`，TimesFM 2.5 为 `5a9806b9b291fad9233b5249d88263f1846304d3`。TTM 记录适配器解析出的 revision。
- [x] AC6 仓库 diff 不包含控制系统写入、新基座或预测语义变更。若没有代码修复，产品代码 diff 为空。

## 备注

- 历史归档的七个预测运行：val 1,728 个起点 / `e51e301e6b09`，test 1,735 个起点 / `07c9ced03282`。
- 任务状态保持 `planning`，直到这些工件经确认后再执行 `task.py start`。
