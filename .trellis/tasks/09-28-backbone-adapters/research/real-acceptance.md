# 步骤 7：真实检查点与 GPU 验收

日期：2026-09-29。工作目录：`D:\Documents\Code\Python\Exp\tsllm`。基线：`3bb3a92`；分支：`codex/backbone-adapters`。步骤 6 独立审查已通过后开始本验收。所有模型输入均为合成正弦/余弦序列；未读取 `data/` 或 `ref/`。

当前结论：AC5 的 3 项和 AC6 的 2 项均已通过真实验收。首次整轮为 4 过 1 失败，TTM 局部修复后的定向复测通过；首次失败日志完整保留。修复后离线四项质量检查全部通过。

## 环境

环境命令在 2026-09-29 00:22:18 -05:00 执行，退出码 0。

| 项目 | 实际值 |
| --- | --- |
| OS / Python | Windows 11 10.0.26200 / 3.13.11 |
| GPU / 驱动 | NVIDIA GeForce RTX 5090 Laptop GPU / 617.14 |
| GPU 总显存 | 24,463 MiB（nvidia-smi） |
| torch / CUDA runtime | 2.11.0+cu128 / 12.8 |
| CUDA 可用 / capability / bf16 | True / (12, 0) / True |
| transformers / peft | 5.17.0 / 0.21.0 |
| chronos-forecasting / granite-tsfm | 2.3.2 / 0.3.9 |
| huggingface-hub | 1.33.0 |

## 首次命令

```powershell
Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
Remove-Item Env:TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue
Remove-Item Env:UV_OFFLINE -ErrorAction SilentlyContinue
$env:HF_ENDPOINT = 'https://hf-mirror.com'
uv run pytest -m 'weights or gpu' -s
```

三个 offline 环境变量只在本命令进程清除。终端输出保留到已忽略的 `cache/backbone-real-acceptance-first.log`，没有覆盖先前验收日志。收集 126 项，选择 5 项，121 项排除。

## 首次结果

退出码 1；4 passed、1 failed、121 deselected；121.79 s。Chronos2 和 TimesFM25 的 AC5/AC6 均通过。TTM 首次预测失败，尚未执行该模型的 5 步微调。首轮失败保留，不以其他模型的通过结果替代。

| 项目 | 模式 / dtype / 实际设备 | 加载 / 预测 / 训练 / 总耗时 (s) | 峰值分配显存 (MiB) | 结果 |
| --- | --- | --- | --- | --- |
| Chronos2 AC6 | zero_shot / bf16 / cuda:0 | 45.652 / 15.685 / 不适用 / 61.337 | 237.655 | 通过 |
| TimesFM25 AC6 | zero_shot / bf16 / cuda:0 | 44.256 / 0.165 / 不适用 / 44.421 | 453.515 | 通过 |
| Chronos2 AC5 | lora / fp32 / cuda:0 | 1.645 / 0.074 / 2.133 / 3.879 | 962.235 | 通过 |
| TimesFM25 AC5 | lora / fp32 / cuda:0 | 1.461 / 0.039 / 1.138 / 2.695 | 960.487 | 通过 |
| TTM AC5 | head / 请求 fp32 / 请求 cuda | load调用0.00004；首预测失败；总6.727 | 20.350 | 失败 |

AC6 首轮加载耗时包括下载及模型初始化。AC5 两个已通过模型使用同轮已下载缓存。TTM 延迟到首次 forecast 调用内加载模型；失败记录没有将 load() 返回视为加载或预测成功。

### resolved revision

- Chronos2：`amazon/chronos-2`，`29ec3766d36d6f73f0696f85560a422f50e8498c`。
- TimesFM25：`google/timesfm-2.5-200m-transformers`，`5a9806b9b291fad9233b5249d88263f1846304d3`。
- TTM：`ibm-granite/granite-timeseries-ttm-r2`，选择分支 `512-48-ft-r2.1`，实际 snapshot commit `b972f0c22190b7502764526004d16e2b4ed39e8c`。该值取自本次库加载日志，不是仓库 main 分支 commit。

### AC5 参数和进度

| 模型 | 可训练参数 / 全部参数 | 比例 | 实际步骤 |
| --- | --- | --- | --- |
| Chronos2 LoRA | 1,206,912 / 120,684,576 | 1.000055% | [1, 2, 3, 4, 5] |
| TimesFM25 LoRA | 2,457,600 / 233,746,880 | 1.051394% | [1, 2, 3, 4, 5] |

两个 LoRA 比例均严格大于 0 且小于 5%，由训练前 Reporter 参数统计获得，在任何适配权重 reload 前保留。两项均验证准确 5 次更新与 5 个有限损失。

- Chronos2 5 步损失：`[0.29076886, 0.65745318, 0.29403865, 0.49828357, 0.38032538]`。
- TimesFM25 5 步损失：`[0.01724184, 0.01700313, 0.01741847, 0.01511739, 0.01742748]`。

本次两项 5 步首末损失未下降，未将其记为损失下降。AC5 要求真实检查点完成 5 步；损失下降的独立验收由离线随机模型的 20 步测试覆盖。

### TTM 首次失败

- 原始异常：`Exception: Expecting freq_token in forward`，位于锁定库 `tsfm_public/models/tinytimemixer/modeling_tinytimemixer.py:3085`。
- 选中的真实检查点启用 `resolution_prefix_tuning`；适配器此前未向 forward 传递 token。随机微型模型默认未启用 prefix，因此原离线测试未覆盖该路径。
- 已通知主会话，并暂停受影响代码修改。主会话同步子设计 §4.6 与 model-adapter spec 后批准局部补齐。检查点、阈值和公共协议未改变。

## TTM 锁定库证据与修复

以下行号对应本机 `.venv/Lib/site-packages/tsfm_public/` 中 granite-tsfm 0.3.9 的源码。

- `toolkit/time_series_preprocessor.py:44-57`：默认映射为 OOV=0、min=1、2min=2、5min=3、10min=4、15min=5、30min=6、h/H=7、d/D=8、W=9。
- `toolkit/time_series_preprocessor.py:646-668`：`get_frequency_token` 先精确查询，再通过 pandas offset 或 Timedelta 规范化；合法但无映射的值发出库 warning 并返回 OOV=0。非法字符串仍抛 ValueError。
- `toolkit/time_series_preprocessor.py:1057-1058`：官方数据集构建使用该映射方法。
- `models/tinytimemixer/modeling_tinytimemixer.py:3010-3019`：根据实际词表大小建立 prefix embedding。`:3070-3085`：prefix 模型缺少 token 会报首次异常；输入 token 形状为 `(B,)`，库内部转 long。
- 本次真实检查点配置：prefix=True、frequency_token_vocab_size=10、原生 L=512、H=48。
- 本地映射验证：`1min→1`、`5min→3`、`1h→7`；`60s→0`、`10s→0` 并伴随库警告；`bogus` 为 ValueError。适配器保留该库语义，没有将 60s 自行改成 min。

局部修复仅位于 `src/tsllm/backbones/ttm.py`：

1. `_frequency_token(freq, reporter)` 仅在 prefix 开启时调用官方方法。OOV 另向调用方 Reporter 发出明确警告，非法频率抛 ValueError，token 超过实际词表边界抛 CapabilityError。
2. `_inputs` 按批次创建同设备的 `(B,)` long token。未开启 prefix 时不添加 token。
3. `forecast` 使用 `ContextBatch.freq`；`finetune` 使用 `SegmentSet.freq`。验证集频率不一致时，在参数更新前拒绝。

### 随机小模型回归

- 新增 `resolution_prefix_tuning=True`、词表大小 10 的实际随机 TTM。
- 首次复现命令：`uv run pytest tests/backbones/test_ttm_tiny.py -k 'prefix_frequency' -s`；exit 1，4 failed、6 deselected，6.69 s。日志：`cache/backbone-ttm-prefix-regression-first.log`。
- 修复后专项命令：`uv run pytest tests/backbones/test_ttm_tiny.py -s`；exit 0，10 passed，6.79 s。日志：`cache/backbone-ttm-prefix-regression-retest1.log`。
- 覆盖映射频率与 OOV、预测/训练/固定验证 token 的 dtype/device/shape、非法频率、词表越界、验证频率不一致拒绝及无参数更新。原 prefix=False 检查点的全部测试保持通过。
- 验收 JSON 输出增强时的单个 Ruff B009 已修正为显式属性访问；没有关闭 lint 规则。

## TTM 真实定向复测

在同样的进程级 offline 变量清除与 HF_ENDPOINT 设置后执行：

```powershell
uv run pytest -m weights tests/backbones/test_smoke_weights.py -k ttm -s
```

退出码 0；1 passed、2 deselected；23.62 s。日志：`cache/backbone-real-acceptance-ttm-retest1.log`。只复测首轮失败的 TTM；其余 4 项已通过且行为未修改，没有重复运行。

| 指标 | 实际结果 |
| --- | --- |
| 分支 / resolved revision | 512-48-ft-r2.1 / b972f0c22190b7502764526004d16e2b4ed39e8c |
| 模式 / 参数 dtype / 参数 device | head / torch.float32 / cuda:0 |
| 可训练参数 / 全部参数 | 246,818 / 799,756 |
| 可训练比例 | 30.861663%；head 模式不适用 LoRA 的 5% 阈值 |
| 实际更新步骤 | [1, 2, 3, 4, 5] |
| load() 调用 | 0.000044 s；该调用只保存配置 |
| 首次 forecast（含延迟加载） | 16.133299 s |
| 5 步训练 | 5.803649 s |
| 模型验收总耗时 | 21.941709 s |
| 峰值分配显存 | 24.113770 MiB |

5 步损失：`[0.45114183, 0.43457979, 0.44532937, 0.44888610, 0.42573625]`。零样本与训练后预测均为 `(1,2,16)` 且数值有限；5 次更新与 5 个有限训练损失断言通过。

首次预测时间包括延迟模型加载和 CUDA 首次执行，未拆分为缺少测量依据的独立数值。GPU 显存采用 `torch.cuda.max_memory_allocated()`，不等于驱动报告的进程总显存。

## 修复后的离线质量检查

默认 pytest 使用 `UV_OFFLINE=1`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`，仅执行合成数据和随机小模型测试。

| 命令 | 结果 |
| --- | --- |
| `uv run ruff check` | exit 0，All checks passed |
| `uv run ruff format --check` | exit 0，57 files already formatted |
| `uv run pyright` | exit 0，0 errors, 0 warnings, 0 informations |
| `uv run pytest` | exit 0，125 passed, 5 deselected, 2 warnings，11.97 s |

日志：`cache/backbone-real-final-ruff.log`、`cache/backbone-real-final-format.log`、`cache/backbone-real-final-pyright.log`、`cache/backbone-real-final-pytest.log`。2 条警告来自 Chronos 在有 CUDA 的机器上执行 CPU 随机小模型训练；没有过滤警告。

`git diff --check` exit 0，仅输出已有 LF/CRLF 提示。`git check-ignore` 确认真实首轮、TTM 复测和 prefix 首次回归日志都被忽略。模型权重保存在本机 Hugging Face 缓存，不在项目 Git 范围内。

## 验收结论与待完成项

AC5 的 3 个真实检查点及 AC6 的 2 个 CUDA+bf16 项均已取得通过证据。AC7 已由环境命令实际确认。首轮 TTM 失败及修正后复测分开保留。

本步骤修改范围：`src/tsllm/backbones/ttm.py`、`tests/backbones/test_ttm_tiny.py`、`tests/backbones/test_smoke_weights.py`、`tests/backbones/test_cuda.py` 和本验收记录。未修改父共享契约、配置字段、依赖或数据接口。

本步骤完成后释放源码和测试所有权。主会话仍需派发最终全范围 trellis-check，并完成 Phase 3.3 状态核验与 Phase 3.4 提交方案。未 commit、archive 或 push。
