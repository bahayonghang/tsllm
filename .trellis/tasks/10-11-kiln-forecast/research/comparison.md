# 回转窑预测对比

记录时间：2026-10-12。七个正式运行都成功，`error` 为空。源文件字节数 1,068,005,224，与归档指纹相同。验证集 1,728 个起点，哈希 `e51e301e6b09`；测试集 1,735 个起点，哈希 `07c9ced03282`。七个运行的这两个哈希相同。

模型取舍只看 val 的 `mae_norm_macro`，下表已按该值从小到大排列。test 未用于选型。

GPU 运行使用空闲的第二块 RTX 4090（`CUDA_VISIBLE_DEVICES=1`）。配置文件里的 `device: cuda` 没有修改。

## 结果

| 运行 | 基座 | 模式 | 状态 | revision | val mae | val rmse | test mae | test rmse | 起点 | load_s | train_s | peak_vram_mb |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `20261012-053618-kiln-chronos2-lora-34c0` | chronos2 | lora | succeeded | `29ec3766d36d6f73f0696f85560a422f50e8498c` | 0.179895 | 0.339324 | 0.161625 | 0.358207 | val 1728 / `e51e301e6b09`；test 1735 / `07c9ced03282` | 1.763 | 43.813 | 1554.4 |
| `20261012-052845-kiln-chronos2-zero-shot-0826` | chronos2 | zero_shot | succeeded | `29ec3766d36d6f73f0696f85560a422f50e8498c` | 0.183449 | 0.344552 | 0.164926 | 0.364693 | 同上 | 1.760 | — | 390.0 |
| `20261012-053737-kiln-timesfm25-lora-6d99` | timesfm25 | lora | succeeded | `5a9806b9b291fad9233b5249d88263f1846304d3` | 0.188003 | 0.344689 | 0.169513 | 0.362308 | 同上 | 2.205 | 94.119 | 1212.5 |
| `20261012-052912-kiln-timesfm25-zero-shot-6fed` | timesfm25 | zero_shot | succeeded | `5a9806b9b291fad9233b5249d88263f1846304d3` | 0.191115 | 0.349395 | 0.172598 | 0.368362 | 同上 | 350.061 | — | 771.3 |
| `20261012-053541-kiln-ttm-zero-shot-8bc7` | ttm | zero_shot | succeeded | `6e5cb8ee51e0634a45637490f5db43148b2fa6be` | 0.195890 | 0.355689 | 0.180262 | 0.377417 | 同上 | 0.000 | — | 36.0 |
| `20261012-051248-kiln-persistence-8533` | persistence | zero_shot | succeeded | — | 0.209289 | 0.379108 | 0.190875 | 0.396885 | 同上 | 0.000 | — | — |
| `20261012-051251-kiln-ridge-ea58` | ridge | full | succeeded | — | 0.227085 | 0.400323 | 0.216174 | 0.416397 | 同上 | 0.000 | 1.594 | — |

mae、rmse 是 `mae_norm_macro` 和 `rmse_norm_macro`。每个正式运行都有 `predictions/val.parquet` 和 `predictions/test.parquet`。两个 LoRA 运行的 `adapter/` 已写好。训练目标来自 fit 段；val 段只记录 `val_loss`。

按 val `mae_norm_macro`，Chronos-2 LoRA 最低。TimesFM 2.5 的零样本 load 含检查点下载，约 350 秒。

## 备注

- 没有 warning 写入 `metrics.json`。
- TTM 的 YAML revision 为空。运行日志写明：revision 未固定，解析结果为 `6e5cb8ee51e0634a45637490f5db43148b2fa6be`；请求上下文 120 步，检查点原生长度 90 步。`effective_context_length=90`。
- Chronos-2 与 TimesFM 2.5 给出分位数。TTM、保持值和岭回归没有 pinball 或区间覆盖率。
- `20261012-051409-kiln-chronos2-zero-shot-ed39` 在首次下载中被掐断，状态是 `interrupted`，不进入上表。随后的 Chronos-2 零样本是 `…-0826`。
- `20261012-053948-kiln-timesfm25-lora-9790` 是 TimesFM 2.5 LoRA 的一次重复运行。05:39:48 开始，05:41:39 结束，状态 `succeeded`，`error` 为空。revision 同为 `5a9806b9b291fad9233b5249d88263f1846304d3`。val / test 的 `mae_norm_macro` 与 `rmse_norm_macro` 和 `…-6d99` 逐位相同；起点哈希也相同。`train_seconds` 为 95.982，第一次是 94.119。上表只用先完成的 `…-6d99`。

## 验收核对

- AC1：`research/ingest.md` 已记录源指纹、缓存哈希 `2346cbf01957`、有效分钟 523,782。相对 523,702 的偏差为 +0.015276%。
- AC2：上表七个运行均为 `succeeded`，`error` 为空。
- AC3：源字节数未变，val / test 哈希等于归档值。
- AC4：本文件包含七行结果、val 排序，以及 test 未用于选型。
- AC5：六个需要权重的运行都记录了解析 revision。TTM 的 revision 由适配器解析。
- AC6：产品代码没有改动。工作区新增内容只在 `.trellis/tasks/10-11-kiln-forecast/`。
