# 依赖与接口核对

核对日期：2026-09-28。方法：`uv pip compile --python-version 3.13` 解析版本；`uv pip install --no-deps` 安装到临时环境后读源码。未在 GPU 上运行任何模型。

## 本机环境

| 项目     | 值                                                                                    |
| -------- | ------------------------------------------------------------------------------------- |
| OS       | Windows 11 Pro 10.0.26200                                                             |
| GPU      | NVIDIA GeForce RTX 5090 Laptop GPU，24,463 MiB，驱动 617.14（Blackwell，sm_120）      |
| Python   | 项目 `.python-version` = 3.13；`pyproject.toml` 要求 `>=3.13`                         |
| 包管理   | uv 0.12.19，构建后端 `uv_build`                                                       |
| Node     | v26.7.0；pnpm 12.8.0；npm 12.1.0；bun 1.4.2                                           |
| 网络     | `pypi.org`、`huggingface.co` 直连 curl 失败；uv 可解析 PyPI；`hf-mirror.com` 返回 308 |
| 权重缓存 | `~/.cache/huggingface/hub` 无 Chronos / TimesFM / TTM 权重                            |

## 版本解析（Python 3.13）

| 组合                                      | 结果                                                                                                           |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| chronos-forecasting + transformers + peft | chronos-forecasting 2.3.2，transformers 5.17.0，peft 0.21.0，torch 2.14.0，numpy 2.5.3                         |
| 上述 + granite-tsfm                       | granite-tsfm 0.3.9，torch 降为 2.11.0，其余不变                                                                |
| 上述 + momentfm                           | momentfm 0.1.4 锁定 transformers 4.33.3、numpy 1.25.2，chronos-forecasting 被降到 1.5.0，granite-tsfm 无法共存 |
| torch 2.11 CUDA 轮子（Windows）           | `https://download.pytorch.org/whl/cu128` 与 `cu130` 均有 `torch==2.11.0`                                       |

约束：

- granite-tsfm 0.3.9 要求 `Requires-Python <3.14,>=3.11`、`torch<2.12,>=2.10`、`transformers[torch]<6,>=4.57.6`、`scikit-learn<1.8`。
- chronos-forecasting 2.3.2 要求 `transformers<6,>=4.41`、`torch<3,>=2.2`；LoRA 需要 extra `peft<1,>=0.18.1`。
- RTX 5090 需要 CUDA 12.8 及以上构建的 torch。主环境锁定 `torch==2.11.*` + cu128 索引。
- MOMENT（momentfm）不能进入主环境。需要时使用独立 uv 环境，由任务执行器按后端声明的解释器启动。

## Chronos-2（`chronos.chronos2.pipeline.Chronos2Pipeline`）

- `fit(inputs, prediction_length, validation_inputs=None, finetune_mode="full"|"lora", lora_config=None, context_length=None, learning_rate=1e-6, num_steps=1000, batch_size=256, output_dir=None, min_past=None, ...) -> Chronos2Pipeline`，返回新的 pipeline。
- `finetune_mode="lora"` 且未安装 peft 时，发出警告并回退到 full。适配器必须在调用前检查 peft 可导入，回退视为错误。
- `batch_size` 按序列数计（目标 + 协变量），不等于多变量窗口数。
- `predict(inputs, prediction_length, batch_size, context_length, cross_learning=False)`：输入可为 `(batch, n_variates, T)` 张量或字典列表（`target`、`past_covariates`、`future_covariates`）。返回每个输入一个分位数张量。
- `predict_quantiles`、`predict_df` 可用。
- `embed(inputs, batch_size, context_length) -> (embeddings, loc_scale)`，每个元素形状 `(n_variates, num_patches + 2, d_model)`。分类任务用该接口取冻结表示。
- 输入允许 NaN 表示缺失。

## TimesFM 2.5（`transformers.TimesFm2_5ModelForPrediction`，transformers 5.17.0）

- 配置默认 `patch_length=32`、`context_length=16384`、`horizon_length=128`。
- `forward(past_values: Sequence[1D Tensor], window_size=None, future_values=None, forecast_context_len=None, truncate_negative=None, force_flip_invariance=None)`；提供 `future_values` 时返回 `loss`（MSE + 分位数损失）。
- 输入为单变量序列列表；多通道按通道拆分为独立序列（共享单变量）。
- 内部做实例归一化，外部输入原始值。
- 官方 LoRA 示例：`https://raw.githubusercontent.com/google-research/timesfm/master/timesfm-forecasting/examples/finetuning/README.md`（未在本次重新下载）。

## Granite TSFM（`tsfm_public`，granite-tsfm 0.3.9）

- 模型：`tinytimemixer`（TTM）、`tspulse`、`flowstate`、`patchtst_fm`。
- `tsfm_public.toolkit.get_model` 按上下文长度与预测长度选择 TTM 检查点。
- TSPulse 提供 `TSPulseForClassificationOutput`；toolkit 含 `time_series_classification_pipeline.py` 与 `time_series_classification_preprocessor.py`。
- TTM 需要外部按通道缩放（toolkit `TimeSeriesPreprocessor`），缩放统计只能来自拟合段。

## Web 相关版本（单独解析，未做联合解析）

fastapi 0.141.1；polars 1.44.2。前端依赖在 web-ui 子任务中锁定。

## 许可

| 模型                  | 许可要点                                 | 本轮处理 |
| --------------------- | ---------------------------------------- | -------- |
| Chronos-2             | Apache-2.0                               | 纳入     |
| TimesFM 2.5           | 以实施时模型卡为准，锁定 revision 时记录 | 纳入     |
| Granite TTM / TSPulse | 以实施时模型卡为准                       | 纳入     |
| TimesFM-3             | 非商业、非生产许可，覆盖微调派生模型     | 不纳入   |
| Toto 2.0              | 官方 2.0 微调与外生变量未开放            | 不纳入   |
