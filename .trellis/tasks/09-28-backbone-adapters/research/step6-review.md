# 步骤 6 独立质量审查

日期：2026-09-29。基线：`3bb3a92`。范围：全部适配器、配置、注册表、检查点、依赖声明及新增/修改测试。审查代理未修改父子规划、spec、依赖锁文件或任务元数据；主会话负责文档同步。

## 结论

步骤 6 的离线质量门禁通过。修复 3 类已复现问题；最终默认测试为 121 passed、5 deselected、2 warnings。无新增共享契约变更或阻塞步骤 7 的未决代码问题。

本记录不代表 AC5、AC6 通过。本审查没有下载或加载真实权重，没有执行 CUDA 模型测试。AC7 的已执行证据仍以 `research/dependency-validation.md` 为准，本审查未重复 GPU 验收。

## 已修复问题

### 1. 验证通道顺序未校验

- 文件：`src/tsllm/backbones/training.py`。
- 原行为：TimesFM/TTM 共享训练循环接受与训练集通道顺序不同的验证集，可能对错误通道应用训练缩放和验证选择。
- 复现：`test_training_rejects_validation_channel_order` 首次失败，未抛出预期异常。
- 修复：抽样和参数更新前校验 `val.channel_names == train.channel_names`。
- 回归：断言顺序不匹配时无参数更新；另用真实 torch 优化器验证固定验证窗口复用及最低验证损失权重恢复。原有三类实际随机小模型训练测试保留。

### 2. 模型加载失败绕过领域异常

- 文件：`checkpoint.py`、`chronos2.py`、`timesfm25.py`、`ttm.py`、`ridge.py`。
- 原行为：三个模型对空本地检查点抛出原始库异常，未满足 `BackboneLoadError` 契约；仅检查 peft 的可发现性也不足以证明 peft 可以导入。
- 复现：三个 `test_invalid_model_checkpoint_is_domain_error` 参数项首次均失败。
- 修复：窄范围加载边界转换 ImportError、OSError、ValueError、RuntimeError；加载错误保留模型/检查点标识及异常类别，抑制可能包含配置内容的底层异常链。LoRA 训练前验证 peft 可以实际导入；禁止改为 full。Ridge 缺少 sklearn 时同样产生领域异常。
- 回归：实际空检查点、缺失模型依赖和 Chronos peft 导入失败均有测试；已保留无 peft 时不回退 full 的原测试。新增独立进程测试，使用空 HF 缓存和禁止 socket 连接的守卫，验证 HF_ENDPOINT、HF_HUB_OFFLINE 及离线失败路径。

### 3. TTM 后续预测覆盖保存身份

- 文件：`src/tsllm/backbones/ttm.py`。
- 原行为：首次加载/训练为 L=32、H=8 后，L=24、H=4 的预测将保存元数据改为 24/4。HF 重载可能因此选择不同检查点分支。
- 复现：`test_ttm_save_preserves_loaded_selection_dimensions` 首次得到 24/4，期望 32/8。
- 修复：首次模型选型的 L/H 与后续预测尺寸分离；保存 resolved revision；重载拒绝已知 revision 不一致。重置模型时清除旧 resolved checkpoint 及上下文报告状态。
- 回归：真实小模型训练、变更预测尺寸、保存/重载的预测一致性，以及 revision 不匹配拒绝。实际有效上下文长度仍按当前预测请求报告。

其他局部边界修正：训练模式检查显式拒绝 zero_shot；Chronos 重新 load 清除旧适配目录引用。共享 load/finetune 签名、序列化配置和数据接口不变。

## 补充验证

- 6 项注册表、能力矩阵、Options schema 和独立新进程的惰性导入通过。
- 数据契约中原 pytest 进程的 sys.modules 断言会受到实际小模型测试导入影响。删除该重复断言后，AST 检查和独立进程的无重型导入断言完整保留；原数据契约测试全部通过。
- 新增 TimesFM 缺失目标丢弃/全空目标拒绝、TTM 部分目标掩码/全空目标拒绝及非单位 FitStats 的通道缩放测试。
- 实际随机 TimesFM、TTM、Chronos 模型继续完成 20 步训练损失下降和适配权重往返。TTM 主干冻结检查保持逐元素相等，解码器与预测头训练路径保留。
- Chronos 原生训练数据集以 min_past + prediction_length 过滤短段；在单段内选取完整目标。验证使用每段最后一个窗口，库训练器保留最佳验证检查点。审查依据为安装版本源码，未修改第三方库。
- 已准备 AC5 的真实测试要求 5 个实际训练进度步骤和 5 个有限损失，LoRA 可训练参数比例严格大于 0 且小于 5%；比例在任何 adapter reload 前读取。AC6 另断言实际参数位于 CUDA 且 dtype 为 bf16。两组测试本次未运行。
- 已检查主会话同步的“权重下载失败必须保留失败并复测”规则。强制真实验收不能通过 skip 完成。
- 主会话已将实际实现/测试路径同步至相关 spec；新增范围未在本审查中提前标记 Verified。

## 命令结果与首次失败证据

环境：UV_OFFLINE=1、HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1。测试仅用合成数据及临时目录生成的小模型；未读取 data/ 或 ref/。

| 阶段 | 命令 | 结果 |
| --- | --- | --- |
| 初次独立门禁 | uv run ruff check | exit 0，All checks passed |
| 初次独立门禁 | uv run ruff format --check | exit 0，56 files already formatted |
| 初次独立门禁 | uv run pyright | exit 0，0 errors, 0 warnings, 0 informations |
| 初次独立门禁 | uv run pytest | exit 0，108 passed, 5 deselected, 2 warnings，10.98 s |
| 新增复现测试 | 定向 pytest | exit 1，5 failed, 1 passed, 9 deselected，7.05 s |
| 修复后专项复测 | uv run pytest tests/backbones | exit 0，33 passed, 5 deselected, 2 warnings，9.31 s |
| 最终门禁 | uv run ruff check | exit 0，All checks passed |
| 最终门禁 | uv run ruff format --check | exit 0，57 files already formatted |
| 最终门禁 | uv run pyright | exit 0，0 errors, 0 warnings, 0 informations |
| 最终门禁 | uv run pytest | exit 0，121 passed, 5 deselected, 2 warnings，12.01 s |

2 条警告均来自 Chronos 在有 CUDA 的机器上执行 CPU 小模型训练的提示。未过滤这些警告。修复阶段的导入排序及 2 个 E501 已由 Ruff 格式化修正，最终门禁无 lint/type 错误。

日志保留在忽略的 cache/：`step6-review-first-*.log`、`step6-review-regressions-first.log`、`step6-review-regressions-retest1.log`、`step6-review-retest1-pyright.log`、`step6-review-final-*.log`。首次失败没有覆盖。

另执行 `uv lock --check --offline`：exit 0，Resolved 101 packages；`git diff --check`：exit 0，只有 Git 的 LF/CRLF 提示。

## 未修复事项与后续范围

- TimesFM 库内分位数损失索引语义限制：证据已在 `research/library-api-audit.md` 保留。子设计明确使用库 forward.loss，本审查未改写第三方损失。若改变损失定义，需要单独决策。
- AC5、AC6 仍需主会话执行本机真实权重与 GPU 验收；不能以本次离线测试代替。
- 最终全范围 trellis-check 和 Phase 3.3 Verified 状态核验仍需在真实验收后执行。
- 未 commit、archive 或 push；未实施 experiment-runner、service-api 或 web-ui。

本审查完成后释放源码、测试及依赖文件的代码所有权，交由主会话协调步骤 7。
