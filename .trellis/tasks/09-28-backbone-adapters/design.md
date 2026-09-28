# 适配层设计

共享契约以父任务 `design.md` 第 5 节为准。本文件细化模块、各适配器实现与测试方式。

## 1. 模块

```text
src/tsllm/
  config/backbone.py        # BackboneConfig、FinetuneConfig、LoraSpec
  backbones/
    __init__.py             # 导入各适配器模块以完成注册（模块顶层不得导入重型库）
    base.py                 # Capabilities、ForecastOutput、Backbone、CapabilityError、BackboneLoadError
    registry.py             # register_backbone、get_backbone、list_backbones、BackboneInfo
    checkpoint.py           # resolve_checkpoint(cfg) -> ResolvedCheckpoint(path, revision, source)
    windows.py              # sample_training_windows(segment_set, L, H, n, rng)：微调用随机窗口
    nan.py                  # 上下文 NaN 填补工具：interpolate_1d、ffill_bfill
    training.py             # timesfm25 与 ttm 共用的训练循环：抽样、验证、保留最优权重（见 4.6）
    persistence.py
    ridge.py
    features.py
    chronos2.py
    timesfm25.py
    ttm.py
```

`backbones/windows.py` 只在拟合段 `SegmentSet` 内抽样，窗口不跨数组边界。抽样按数组长度加权，使用调用方传入的 `numpy.random.Generator`。

## 2. 配置

```python
class LoraSpec(StrictModel):
    r: int = 8
    alpha: int = 16
    dropout: float = 0.05
    target_modules: list[str] | None = None   # None 表示使用适配器默认值

class FinetuneConfig(StrictModel):
    learning_rate: float = 1e-5
    num_steps: int = 1000
    batch_size: int = 64
    eval_every: int = 100            # 验证间隔（步）
    grad_clip: float = 1.0
    lora: LoraSpec = LoraSpec()

class BackboneConfig(StrictModel):
    name: str
    checkpoint: str | None = None    # 基线为 None
    revision: str | None = None
    device: Literal["cuda", "cpu"] = "cuda"
    dtype: Literal["fp32", "bf16"] = "bf16"
    options: dict[str, Any] = {}
```

`options` 在 `load()` 开头用适配器的 `Options` 模型校验。

## 3. 注册信息

```python
class BackboneInfo(BaseModel):
    name: str
    capabilities: Capabilities
    options_schema: dict           # Options.model_json_schema()
    requires: list[str]            # 顶层导入名，如 ["torch", "chronos"]
    installed: bool                # 全部 requires 的 find_spec 非 None
    default_checkpoint: str | None
    license: str | None            # 例如 "Apache-2.0"
    license_url: str | None
```

## 4. 各适配器

### 4.1 persistence

- 预测：每个 (b, c) 取上下文最后一个非 NaN 值重复 H 次；全 NaN 时输出 NaN。
- 无 quantiles。

### 4.2 ridge

- Options：`alpha: float = 1.0`、`max_samples: int = 50000`、`seed: int = 0`。
- `finetune()`：从 `SegmentSet` 抽取 `max_samples` 个窗口；输入按 FitStats 标准化后展平为 `C×L`，NaN 置 0（即拟合均值）；目标标准化后展平为 `C×H`；目标含 NaN 的样本丢弃。
- 预测：反标准化到物理单位。
- `save_adapter`：`joblib` 或 `numpy.savez` 保存系数与截距。

### 4.3 features

- `embed()`：每通道计算 nanmean、nanstd、最后一个非 NaN 值、最小二乘斜率（忽略 NaN）、nanmin、nanmax，输出 `(B, 6C)`；全 NaN 通道输出 0 并在 reporter 中计数警告。

### 4.4 chronos2

- Options：`quantile_levels: list[float] | None`（None 用模型默认）、`embed_channel_pool: Literal["concat", "mean"] = "concat"`、`predict_batch_size: int = 256`。
- `load()`：`Chronos2Pipeline.from_pretrained(path, device_map=device, torch_dtype=...)`。
- 预测：`pipeline.predict(torch.tensor(values), prediction_length=H, context_length=L, cross_learning=False)`，NaN 直接传入；`mean` 取 0.5 分位数。
- 微调：`mode` 为 `lora` 时先 `importlib.util.find_spec("peft")`，缺失抛 `BackboneLoadError`；调用 `pipeline.fit(inputs=train.arrays, validation_inputs=val.arrays, prediction_length=H, context_length=L, finetune_mode=..., lora_config=LoraSpec 转换, learning_rate, num_steps, batch_size, output_dir=<临时目录>, callbacks=[ReporterCallback])`，用返回的 pipeline 替换 `self.pipeline`。
- LoRA 生效检查：统计 `requires_grad` 参数数量，写入 reporter metric `trainable_params` 与 `total_params`。
- 保存：`fit()` 输出目录中的最终检查点复制到 `save_adapter(path)`；`load_adapter` 从该目录重新加载 pipeline。
- 表示：`pipeline.embed(values, context_length=L)`；每个元素 `(C, P+2, D)` 去掉最后一个输出 patch token，对 patch 维取平均得 `(C, D)`；按 `embed_channel_pool` 展平或平均。

### 4.5 timesfm25

- Options：`predict_batch_size: int = 512`、`window_size: int | None = None`、`embed_channel_pool` 同上。
- `load()`：`TimesFm2_5ModelForPrediction.from_pretrained(path, torch_dtype=...)`，`max_horizon = config.horizon_length`。
- NaN：每条通道序列先去掉开头连续 NaN（由模型自身左填充处理），内部 NaN 线性插值，末尾 NaN 用最后一个非 NaN 值填补；全 NaN 通道输出 NaN 且不送入模型。
- 预测：`(B, C, L)` 展开为 `B×C` 条一维张量，分批调用 `forward(past_values=list, forecast_context_len=L)`；取均值与分位数输出前 H 步，重排回 `(B, C, H)`。
- 微调（lora）：
  - `peft.LoraConfig(r, lora_alpha, lora_dropout, target_modules)`；默认 `target_modules` 为注意力与 MLP 中的线性层名称，实施时从 `model.named_modules()` 确认并写死在适配器常量中。
  - 每步从拟合段抽 `batch_size` 个 (窗口, 通道) 对，`forward(past_values, future_values)` 取 `loss`。
  - AdamW，梯度裁剪，CUDA 上用 bf16 autocast。
  - 每 `eval_every` 步在固定验证窗口（从 `val` 抽取，种子固定）上计算损失；保留验证损失最低的 LoRA 权重。
- 表示：调用底层 `TimesFm2_5Model` 取最后隐藏层，对 patch 维取平均。
- 保存：`peft` 的 `save_pretrained` 保存 LoRA 权重。

### 4.6 ttm

- Options：`predict_batch_size: int = 256`。
- `load()`：`tsfm_public.toolkit.get_model(path, context_length=L, prediction_length=H)`；`load()` 需要 L 与 H，因此 `ttm` 的 `load` 延迟到首次 `forecast` 或 `finetune` 调用时执行（在 docstring 写明）。不支持的 L / H 组合抛 `BackboneLoadError`，信息中列出可用组合。
- 标准化：按 FitStats 均值与标准差；上下文 NaN 用前向填补后后向填补，仍为 NaN 的置 0（标准化后）。
- 预测：输入 `(B, L, C)`，取 `prediction_outputs` 前 H 步，反标准化。
- head 微调：冻结 `backbone` 参数，只训练解码器与预测头；训练循环与 timesfm25 共用抽样和验证逻辑（放在 `backbones/training.py`，两个适配器调用）。

## 5. 测试

| 文件 | 内容 | 标记 |
|---|---|---|
| `tests/backbones/test_registry.py` | 注册数量、无重型导入、Options schema 可序列化 | 无 |
| `tests/backbones/test_baselines.py` | persistence、ridge、features 数值与 NaN | 无 |
| `tests/backbones/test_timesfm25_tiny.py` | 随机小模型：形状、NaN、损失下降、保存往返 | 无 |
| `tests/backbones/test_ttm_tiny.py` | 同上 | 无 |
| `tests/backbones/test_chronos2_tiny.py` | 若可离线构建小模型则同上，否则并入 weights | 无或 weights |
| `tests/backbones/test_smoke_weights.py` | 3 个真实检查点的加载、预测、5 步微调 | weights |
| `tests/backbones/test_cuda.py` | CUDA + bf16 零样本 | gpu |

随机小模型测试中，"损失下降"定义为 20 步后训练损失低于第 1 步损失，使用固定种子与可学习的合成正弦数据。

## 6. 风险

| 风险 | 处理 |
|---|---|
| transformers 5.x 中 TimesFM 2.5 类的前向参数在后续版本变化 | 锁定 `uv.lock`；适配器集中在一个文件 |
| TTM 不支持 L=120 / H=30 | `get_model` 失败时报出可用组合；任务层允许为 TTM 单独设置 L |
| Chronos-2 `fit()` 在 Windows 上的 DataLoader 多进程问题 | 通过 `extra_trainer_kwargs` 设置 `dataloader_num_workers=0` |
| 权重下载失败 | weights 测试跳过并提示设置 `HF_ENDPOINT` 或本地路径 |
