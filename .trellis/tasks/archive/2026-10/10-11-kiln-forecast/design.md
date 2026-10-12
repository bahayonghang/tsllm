# 阳泉回转窑时序预测设计

## 1. 边界

本任务把 `research/forecast-contract.md` 里的契约跑完，并留下对比记录。

做：

- 入库当前 `yangquan_kiln` 配置。
- 用七个现有预测 YAML 各完成一次运行。
- 核对同一划分的起点哈希。
- 把对比写到本任务 `research/comparison.md`。

不做：

- 不改数据集有效性、重采样、划分比例、上下文长度、预测长度或起点步长。
- 不改适配器的多变量行为。Chronos-2 保持 `cross_learning=False`，TimesFM 2.5 保持通道独立，TTM 保持原生多变量。
- 不新增配置模板，除非某个路径只是笔误且不改变契约。优先直接使用现有 YAML。
- 不新增服务、网页或基座。

产品代码的默认 diff 为空。R7 允许的最小修复必须单独说明，并且不能放宽 C3。

## 2. 数据流

```text
data_in.csv
  -> tsllm data ingest yangquan_kiln
  -> cache/datasets/yangquan_kiln/<config_hash>/
  -> 每个 RunConfig 一个 runs/<run_id>/
  -> research/ingest.md
  -> research/comparison.md
```

入库只负责当前 YAML。`--force` 只在缓存与 YAML 不一致、或画像命令报告缓存过期时使用。源文件字节数变化不是重写有效性规则的理由。

每个实验由 CLI 创建运行目录并在前台执行：

```text
uv run tsllm run configs/runs/<name>.yaml
```

需要权重的命令带 `HF_ENDPOINT=https://hf-mirror.com`。本地缓存已存在时仍记录解析到的 revision。

GPU 运行串行。平台队列同一时刻只跑一个 GPU 任务；本任务用前台 CLI，不并行提交七个运行。

## 3. 运行顺序与可比性

顺序的目的是先锁住窗口清单，再花 GPU 时间：

1. 保持值（CPU，无权重）。
2. 岭回归（CPU，使用全部 18 路）。
3. 三个零样本：Chronos-2、TimesFM 2.5、TTM。
4. 两个 LoRA：Chronos-2、TimesFM 2.5。

第 1 步成功后读取 val/test 的 `n_origins` 和 `origin_set_hash`。后续每个运行必须与它相同。不同则停止，不继续下一个模型。

源文件字节数为 1,068,005,224 时，第 1 步的哈希还必须等于归档值：

| 划分 | 起点数 | `origin_set_hash` |
| --- | ---: | --- |
| val | 1,728 | `e51e301e6b09` |
| test | 1,735 | `07c9ced03282` |

字节数不同时，第 1 步的哈希成为本任务的新基准，并在 `research/ingest.md` 写新指纹。不得为了回到旧哈希去改 YAML。

`cal` 不评价。选型指标是 val 的 `mae_norm_macro`。test 的同一指标只抄录，不作为排序依据。

## 4. 产物

| 路径 | 内容 |
| --- | --- |
| `runs/<run_id>/config.yaml` | 提交时的数据集和运行配置快照 |
| `runs/<run_id>/status.json` | 终态必须是 `succeeded`，`error` 为 null |
| `runs/<run_id>/metrics.json` | `splits.val` 与 `splits.test` 的 overall、per_channel、per_lead、n_origins、origin_set_hash |
| `runs/<run_id>/predictions/{val,test}.parquet` | 长表预测 |
| `runs/<run_id>/env.json` | 需要权重的运行必须有解析后的 revision |
| `runs/<run_id>/adapter/` | 仅两个 LoRA 运行 |
| `research/ingest.md` | 源指纹、缓存哈希、画像计数、划分边界 |
| `research/comparison.md` | 七行结果、哈希一致性、val 排序 |

`runs/` 与 `cache/` 保持未跟踪。`research/*.md` 随任务目录保留。

TTM 日志中的 `effective_context_length` 若不等于 120，写入 `comparison.md` 的备注。这是检查点原生长度，不是失败。

## 5. 失败

| 情况 | 处理 |
| --- | --- |
| 源文件不存在 | 停止。不编造画像数字。 |
| 缓存过期 | 重新入库一次。不改 YAML。 |
| 权重下载失败 | 保留错误。检查镜像和本地缓存后重试该运行一次。仍失败则停止后续 GPU 运行。 |
| 起点哈希不一致 | 停止。先核对是否改过配置或缓存；未改过则按 R7 查缺陷。 |
| 预测含非有限值 | 运行可以是 `succeeded`，但 `metrics.json` 的 warning 必须抄进 `comparison.md`。 |
| 既有代码缺陷阻断运行 | 只修阻断点。修复后从失败的那个运行复跑，不重跑已经哈希一致且成功的运行。 |

最小修复不得改变：通道角色、窗口长度、fit-only 统计、段内窗口、Chronos `cross_learning=False`、TimesFM 通道独立。

## 6. 取舍

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| 任务粒度 | 一个任务，不拆子任务 | 验收是七个运行共享同一起点清单 |
| 入口 | CLI | 验收产物是运行目录；网页只是可选查看方式 |
| 代码变更 | 默认没有 | 平台已能表达这个实验 |
| 选型划分 | val | test 留到全部运行完成之后才解读 |
