# 回转窑预测契约

记录日期：2026-10-11。来源是当前代码和归档验收记录，不是新的数据统计。

## 数据

| 项目 | 值 | 来源 |
| --- | --- | --- |
| 数据集 id | `yangquan_kiln` | `configs/datasets/yangquan_kiln.yaml` |
| 源文件 | `data/阳泉回转窑联合训练孪生样本/data_in.csv` | 同上。`data_out.csv` 在画像中与它逐字节相同，配置不读它 |
| 原始间隔 | 10 s | `native_freq` |
| 模型网格 | 1 min 均值，区间 `(T-1min, T]` 记在右端点 | `src/tsllm/data/prepare.py` 的重采样规则 |
| 通道 | 18 个 DCS 反馈量，角色全部为 `target` | 数据集 YAML |
| 运行态 | `窑头煤反馈 > 5` 且 `高温风机反馈 > 200` | `eligibility` |
| 连续段 | 间隔超过 2 min 断开；短于 6 h 的段丢弃 | `segments` |
| 划分 | 按有效点时间顺序 0.70 / 0.10 / 0.10 / 0.10，对应 fit / val / cal / test | `split` |

归档验收（源文件 1,068,005,224 字节）的 1 min 网格：1,254,823 行，有效分钟 523,782，保留段 43。相对已批准基准 523,702 的偏差为 +0.015276%。划分边界：

| 划分 | 起始 | 结束 | 有效分钟 |
| --- | --- | --- | --- |
| fit | 2023-01-01 00:01:00 | 2024-08-24 16:33:00 | 366,647 |
| val | 2024-08-24 16:34:00 | 2024-10-12 11:10:00 | 52,378 |
| cal | 2024-10-12 11:11:00 | 2025-04-01 19:28:00 | 52,378 |
| test | 2025-04-01 19:29:00 | 2025-05-21 09:43:00 | 52,379 |

数据时间无时区。cal 存在，但本任务的预测配置不评价 cal。

## 窗口

实现：`src/tsllm/tasks/forecast.py`，清单规则在 `src/tsllm/data/windows.py`。

- 起点 `o` 是上下文最后一步。上下文是 `[o-119, o]`，目标是 `[o+1, o+30]`。步长是 1 min。
- 上下文和目标必须属于同一个 `segment_id`。
- 评价起点的目标整体位于 val 或 test；上下文可以使用更早的历史。
- `eval_origin_stride: 30` 使相邻目标窗口首尾相接、互不重叠。
- `eval_leads: [5, 15, 30]` 只是在 30 步预报上额外汇总这三个提前量。

归档七个预测运行的起点：val 1,728 / `e51e301e6b09`，test 1,735 / `07c9ced03282`。

## 模型使用通道的方式

| 配置 | 基座 | 模式 | 通道 |
| --- | --- | --- | --- |
| `kiln_persistence.yaml` | `persistence` | `zero_shot`，CPU | 各通道最后一个非缺失值 |
| `kiln_ridge.yaml` | `ridge` | `full`，CPU | 18 路上下文拼成一个向量，预测 18 路未来 |
| `kiln_chronos2_zero_shot.yaml` | `amazon/chronos-2` | `zero_shot` | `forecast()` 调用 `cross_learning=False` |
| `kiln_chronos2_lora.yaml` | 同上 | `lora`，1000 step，lr `1e-5`，r=8 | 只在 fit 段上训练 |
| `kiln_timesfm25_zero_shot.yaml` | `google/timesfm-2.5-200m-transformers` | `zero_shot` | 通道独立 |
| `kiln_timesfm25_lora.yaml` | 同上 | `lora` | 通道独立，只训 LoRA |
| `kiln_ttm_zero_shot.yaml` | `ibm-granite/granite-timeseries-ttm-r2` | `zero_shot` | `num_input_channels` 为通道数；缩放只用 fit 段 |

固定 revision：Chronos-2 `29ec3766d36d6f73f0696f85560a422f50e8498c`；TimesFM 2.5 `5a9806b9b291fad9233b5249d88263f1846304d3`。TTM 由上下文长度和预测长度选择分支。请求的 120 步可能不等于检查点原生长度，适配器会记录 `effective_context_length`。

`src/tsllm/tasks/validation.py` 对预测任务拒绝 `past_covariate` 和 `known_future_covariate`。`role: ignore` 的通道在读入时被丢掉，不会留在上下文里。

## 指标

`src/tsllm/evaluation/metrics.py`：各通道 MAE / RMSE 使用物理单位。跨通道宏平均先除以 fit 段标准差。分位数模型还有 pinball、80% 区间覆盖率和宽度。预测长表列是 `origin_time, channel, lead, y_true, y_pred`，有分位数时还有 `q_<level>`。

## 明确不做

- 不把 Chronos-2 推理改成 `cross_learning=True`。
- 不把 17 个通道改成协变量来单测一个目标。
- 不跑分类模板。
- 不把预测结果写回控制系统。
