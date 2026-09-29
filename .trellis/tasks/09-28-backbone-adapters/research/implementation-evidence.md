# 适配器实施验证记录

本文件记录实现代理的阶段测试。最终全范围检查和 AC5–AC6 由主会话协调。所有输入均为合成数据，未读取 `data/` 或 `ref/`。详细终端日志位于已忽略的 `cache/`。

## 步骤 2：共享协议与注册表

- 首次测试失败：`ResolvedCheckpoint` 只在 `TYPE_CHECKING` 下导入，但类属性注解在 Python 3.13 的运行时求值，触发 `NameError`，未收集测试。
- 修正：`base.py` 使用 postponed annotations。
- 复测：`uv run pytest tests/backbones/test_contract.py`，5 passed，1.36 s。
- 独立进程命令 `uv run python -c "import tsllm.backbones; import sys; print('torch' in sys.modules)"` 输出 `False`。
- 日志：`backbone-step2-first.log`、`backbone-step2-retest1.log`。

## 步骤 3：基线与窗口

- `uv run pytest tests/backbones`：首次通过，10 passed，2.52 s。
- 覆盖保持值数值与 NaN、6 项特征顺序及斜率、全 NaN 警告、岭回归数值/NaN/目标丢弃/权重往返、插值与填补、随机窗口确定性及不跨数组边界。
- 日志：`backbone-step3-first.log`。

## 步骤 4：TimesFM25 与共享训练

- 在 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1` 下运行真实库配置生成的随机小模型；不下载权重。
- `uv run pytest tests/backbones/test_timesfm25_tiny.py -s`：首次通过，2 passed，6.76 s。
- 20 步 LoRA 训练损失：第 1 步 1.42848182，第 20 步 0.71266925。固定验证窗口执行 4 次；适配权重往返在 `rtol=1e-6, atol=1e-6` 下通过。
- 覆盖 `(B,C,H)`、分位数形状、部分 NaN 后输出有限、全 NaN 通道按契约输出 NaN、表示提取、horizon 上限及 L=30/patch_length=8 内部补齐。
- 研究阶段原始 `forecast_context_len=30` 的 reshape 失败证据由 `library-api-audit.md` 保留；适配器按已同步的子设计补齐内部长度至 32，保持用户数组不变。
- 日志：`backbone-step4-first.log`。

## 步骤 5：TTM

- `uv run pytest tests/backbones/test_ttm_tiny.py -s`：首次通过，4 passed，7.91 s。使用离线生成的随机模型。
- 20 步 head 训练损失：第 1 步 0.53283083，第 20 步 0.00923285；backbone 参数逐元素不变，decoder 参数可训练，权重往返在 `rtol=1e-6, atol=1e-6` 下通过。
- 覆盖上下文 NaN、原生 context 裁剪/补齐警告、horizon 上限、本地未知 revision、用户显式 revision 绕过自动选择、库模型 key 到实际分支映射及不支持组合报错。
- 日志：`backbone-step5-first.log`。

## 步骤 6：Chronos2

- `uv run pytest tests/backbones/test_chronos2_tiny.py -s`：首次通过，4 passed，7.72 s。使用离线生成并保存的随机模型，执行真实库训练。
- 20 步 LoRA 损失：第 1 步 8.00982857，第 20 步 7.93686485；20 步 full 损失：第 1 步 8.00982857，第 20 步 5.93599510。
- 覆盖显式模式传递、full 模式的 `lora_config=None`、新 pipeline 实例、训练参数比例、权重往返、NaN、分位数、表示提取和缺失 peft 时拒绝 LoRA。
- 保留库发出的 2 条 CPU 训练时 CUDA 可用警告；离线默认测试仍在 CPU 执行。
- 日志：`backbone-step6-first.log`。

## 离线全量质量检查

环境设置：`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`。默认 pytest 排除 `weights` 与 `gpu`。

| 命令 | 首次结果 | 修正后复测 |
| --- | --- | --- |
| `uv run ruff check` | 1 个 E501，子进程断言字符串过长 | exit 0，All checks passed |
| `uv run ruff format --check` | exit 0，56 files already formatted | exit 0，56 files already formatted |
| `uv run pyright` | 13 errors | exit 0，0 errors, 0 warnings, 0 informations |
| `uv run pytest` | 108 passed, 5 deselected, 2 warnings，11.60 s | 108 passed, 5 deselected, 2 warnings，10.78 s |

- 类型错误修正：Options 类变量保持共享协议的 `type[BaseModel]`；Chronos 表示返回显式 float32；TTM 工厂返回值和测试具体适配器类型先校验再使用；模型加载与设备迁移拆为两条语句，使用 `device=` 参数。未使用错误忽略或放宽检查配置。
- 原 `tests/data/test_stats_windows.py` 的父 pytest 进程 `sys.modules` 断言会受新增真实随机模型测试影响，已移除该重复断言。原 AST 边界检查和独立新进程的模型库导入检查保持有效。
- 首次失败与复测日志分别保留为 `backbone-gate-first-*.log` 和 `backbone-gate-retest1-*.log`。
- 准备 AC5 的精确 5 步断言后再次检查：Ruff 与格式检查通过；pyright 为 0 errors；默认 pytest 为 108 passed, 5 deselected, 2 warnings，10.54 s。类型和测试日志为 `backbone-gate-final-step6-pyright.log`、`backbone-gate-final-step6-pytest.log`。
- `git diff --check` exit 0；仅提示 Git 的 LF/CRLF 配置警告。

## 待执行

- 步骤 6 后的独立 trellis-check 由主会话派发。
- AC5 三个真实检查点的加载、零样本预测和各 5 步微调尚未执行；对应测试已准备，断言更新序列为 1–5、5 个有限训练损失和 LoRA 训练参数比例，输出 resolved revision、实际步骤、耗时和峰值显存。
- AC6 两个真实检查点的 CUDA + bf16 零样本预测尚未执行；对应测试已准备。
- AC7 已实际通过，详细环境和命令见 `dependency-validation.md`。
