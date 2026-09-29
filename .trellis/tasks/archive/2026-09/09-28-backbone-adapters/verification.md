# 基座适配层实施与验收记录

## 范围与起点

- 起始 HEAD：`3bb3a92`，包含数据契约功能提交 `04bd695`。开始时工作区干净。
- 从该提交新建 `codex/backbone-adapters`，未发现同名分支。
- 已执行 `python ./.trellis/scripts/task.py start 09-28-backbone-adapters`；任务状态为 `in_progress`。
- 本轮仅实施 backbone-adapters。数据契约已归档，其历史验收记录不代替本轮检查。
- 实施开始时未授权提交、归档或推送。最终审查和两组提交方案完成后，用户于 2026-09-29 明确批准两组本地提交及本任务归档；不推送。

## 执行状态

| 步骤 | 状态 | 证据 |
| --- | --- | --- |
| 1 依赖与本机 CUDA | 已完成 | 安装重试退出 0；AC7 输出 `2.11.0+cu128 True (12, 0)`；详见依赖记录 |
| 2 配置、协议、注册表与检查点 | 已完成阶段检查 | 独立进程导入输出 torch False；契约测试 5 passed，1.36 s |
| 3 基线、抽样与缺失值处理 | 已完成阶段检查 | backbones 测试共 10 passed，2.52 s；数值、NaN、Reporter、保存往返与跨段边界 |
| 4 TimesFM 2.5 与共享训练循环 | 已完成阶段检查 | 随机小模型 2 passed，6.76 s；20 步 LoRA 损失 1.42848182 → 0.71266925；保存往返通过 |
| 5 TTM | 已完成阶段检查 | 随机小模型 4 passed，7.91 s；20 步 head 损失 0.53283083 → 0.00923285；主干逐元素不变 |
| 6 Chronos-2 与步骤审查 | 已完成 | 独立审查修复三类问题；四项门禁通过，121 passed；详见 research/step6-review.md |
| 7 真实权重与 GPU 验收 | 已完成 | 首轮 4 passed/1 failed；修复 TTM 频率 token 后相同 revision 定向复测通过 |
| 最终全范围 trellis-check | 已完成，通过 | 125 passed；全部代码、契约、规范、原始验收日志一致；见 research/final-review.md |
| Phase 3.3 规范同步 | 已完成并通过最终核验 | 7 个 backend guide/index 同步实际路径；仅已验证范围标记 Verified，runner/service/web 仍为 Decided |
| Phase 3.4 本地提交 | 已完成 | 依赖提交 `6f94aa2`、功能提交 `c81d304`；2 组共 54 个文件，用户已同时批准本任务归档 |

## 验收状态

AC1–AC7 均已有通过证据。TTM 真实验收暴露的频率输入缺失已修正并复测，随后完整离线四项门禁通过（125 passed）。最终全范围独立审查已通过，无新增代码问题或验收阻塞。所有首次失败与修正后的复测结果分别保留。

| 标准 | 当前证据 |
| --- | --- |
| AC1 | 最终独立 Ruff check/format、Pyright 全绿；离线 pytest 125 passed、5 deselected、2 warnings，12.30 s |
| AC2 | 独立进程列出 6 项；torch、chronos、transformers、tsfm_public、peft、sklearn 均未导入 |
| AC3 | persistence、ridge、features 数值、NaN、通道顺序、拟合缩放及往返测试通过 |
| AC4 | 三库真实配置随机小模型：形状、NaN、20 步损失下降、保存往返；TTM 频率 prefix 回归通过 |
| AC5 | 三个真实检查点均完成加载、零样本预测、准确 5 步微调；两项 LoRA 可训练比例均小于 5% |
| AC6 | Chronos2、TimesFM25 实际参数为 cuda:0 / torch.bfloat16，零样本预测有限且形状正确 |
| AC7 | torch 2.11.0+cu128，CUDA True，capability (12, 0)，bf16 supported True |

## 最终独立质量命令

离线命令在步骤 7 修正和规范同步后执行。代码与证据的全范围人工审查另行记录，不能仅用四项工具通过代替。

| 命令 | 退出码 / 输出摘要 | 命令耗时 |
| --- | --- | --- |
| `uv run ruff check` | 0；All checks passed | 0.177 s |
| `uv run ruff format --check` | 0；57 files already formatted | 0.165 s |
| `uv run pyright` | 0；0 errors、0 warnings、0 informations | 11.247 s |
| `uv run pytest` | 0；125 passed、5 deselected、2 warnings（pytest 12.30 s） | 14.475 s |

两条警告为 Chronos 在有 CUDA 的机器上执行 CPU 小模型训练的库提示，未过滤。日志为已忽略的 `cache/backbone-final-review-{ruff,format,pyright,pytest}.log`。

## 依赖阶段已有证据

- `uv add --frozen` 已写入 PRD R1 的七项新增依赖。torch 使用指定的 `pytorch-cu128` 显式索引；未改变要求的版本范围。
- 首次 `uv lock` 成功，用时 4.17 s，共解析 101 个包。解析版本：torch 2.11.0+cu128、transformers 5.17.0、peft 0.21.0、chronos-forecasting 2.3.2、granite-tsfm 0.3.9、scikit-learn 1.7.2、huggingface-hub 1.33.0。
- 首次 `uv sync` 在下载 torch 时经历代理连接中断及会话中断。恢复检查发现原 exec session 已不存在，日志没有退出码或完成证据，项目环境尚无 torch。因此首次安装不记为通过。
- 恢复后只重试 `uv sync`，不重复 add/lock，不终止其他项目的 uv 进程。原始诊断日志保留在忽略的 `cache/` 下。
- `uv sync` 重试退出 0，总耗时 533.08 s。AC7 原定命令退出 0，耗时 9.01 s，输出 `2.11.0+cu128 True (12, 0)`。`uv pip check` 确认 81 个已安装包兼容。
- 按项目既定 Python 3.13 目标和 granite-tsfm 的 `<3.14` 元信息，将项目声明收窄为 `>=3.13,<3.14`。随后 `uv lock` 和 `uv sync` 均退出 0，共耗时 2.11 s，库版本未变。

## 共享契约门禁

独立 trellis-check 预审确认：既定协议无法将 RunConfig.mode 传入微调，也无法向 features 的 load/embed 路径注入 Reporter。用户回复“批准实施”，批准增加 `finetune(..., *, mode=...)` 与 `load(..., *, reporter=...)`。父共享设计、适配层子设计、规范、JSONL 清单及 experiment-runner 的接口规划已同步；步骤 2–7 获准继续。运行器未开始实施，预审不代替最终全范围质量检查。

## 实施阶段首次失败与修正

- 步骤 2 首次失败：TYPE_CHECKING 类型注解被运行时求值。实施代理添加 postponed annotations 后复测通过；原日志与复测日志分别保留。阶段结果为 5 passed，1.36 s，注册表导入不加载 torch。
- TimesFM 库接口探针：已安装 transformers 5.17.0 将输入直接按 patch_length reshape。patch_length=8、L=30 时出现 RuntimeError，L=32 通过。主会话已将子设计细化为适配器内部向上补齐 patch 长度，保留原始用户窗口与模型掩码。父共享契约不变；该探针执行时尚无适配器回归结果，后续步骤 4 已复测通过。详见 `research/library-api-audit.md`。
- TimesFM 适配器复测：真实 TimesFm2_5Config 随机小模型覆盖 L=30、patch_length=8 的内部补齐；部分 NaN 输入输出有限，全 NaN 通道按约定输出 NaN；表示与 H 上限检查通过。20 步训练损失 1.42848182 → 0.71266925，执行 4 次固定验证，保存/加载预测以 rtol=1e-6 一致。步骤 4 首次适配器测试即通过：2 passed，6.76 s；日志 `cache/backbone-step4-first.log`。
- TTM 库接口探针：granite-tsfm 0.3.9 的 get_model 对本地目录保留 None revision，随后字符串检查触发 TypeError。修正路径为显式传入库内部 revision 标识，同时在 HF 快照解析前完成按 L/H 的分支选择；模型键与分支分别处理。真正本地目录的占位标识不作为 resolved revision。已同步子设计，父协议不变；该探针执行时尚无适配器及权重验收结果，后续步骤 5 和 7 已复测通过。
- TTM 的实际库模型会裁剪或补齐到配置的原生上下文长度。子设计要求 Reporter 记录请求长度和有效长度，并对长度变化发出警告；不引入额外数据或启用 force_return。
- TTM 适配器复测首次通过：4 passed，7.91 s；20 步 head 损失 0.53283083 → 0.00923285。测试覆盖主干参数逐元素不变、decoder 可训练、NaN 有限、上下文长度报告、本地占位值不暴露为 revision、显式 revision 绕过选择器、模型键映射到 main、H 上限与权重往返。日志 `cache/backbone-step5-first.log`。
- Chronos 随机小模型首次通过：4 passed，7.72 s。20 步 LoRA 损失 8.00982857 → 7.93686485；full 损失 8.00982857 → 5.93599510。保留 CPU 测试环境存在 CUDA 时库发出的 2 项警告；未据此改用 GPU。
- 首次完整离线检查：pytest 为 108 passed、5 deselected、2 warnings，11.60 s；Ruff format 为 56 files 通过；Ruff check 有 1 项 E501，pyright 有 13 项类型错误，涉及 Options 类变量、数组返回类型、第三方签名和测试类型收窄。该次运行不满足 AC1；后续实改后的四项门禁通过。首轮日志保留在 `cache/backbone-gate-first-*.log`，不由成功复测覆盖。

## 步骤 6 独立审查

- 实施代理修正首轮 lint/type 问题后，四项门禁通过，默认 pytest 为 108 passed。
- 独立审查新增 5 个失败用例：验证通道顺序未拒绝 1 项；3 个模型的无效本地检查点未转领域异常；TTM 保存尺寸被后续预测覆盖 1 项。首次结果为 5 failed、1 passed、9 deselected，7.05 s，日志未覆盖。
- 修正共享训练入口的通道顺序校验、模型/依赖加载异常边界、TTM 初始选型身份与 revision 校验。新增回归同时覆盖验证窗口复用和最佳权重恢复、缺失目标、缩放、HF 离线环境。未修改父数据契约或放宽断言。
- 最终步骤 6 门禁：Ruff check 退出 0；format 退出 0（57 files）；pyright 退出 0（0 errors、0 warnings）；默认 pytest 退出 0（121 passed、5 deselected、2 warnings，12.01 s）。UV/HF/transformers 均显式离线。
- `uv lock --check --offline`、`git diff --check` 均退出 0。模型真实验收尚未由该审查执行。完整记录：`research/step6-review.md`。

## 步骤 7 真实验收

- 命令：本命令进程清除 HF_HUB_OFFLINE、TRANSFORMERS_OFFLINE、UV_OFFLINE，设置 `HF_ENDPOINT=https://hf-mirror.com`，运行 `uv run pytest -m "weights or gpu" -s`。
- 首轮退出 1：4 passed、1 failed、121 deselected，121.79 s。两个 LoRA 和两个 bf16 验收通过；TTM 所选 `512-48-ft-r2.1` 检查点启用频率前缀，首次预测因缺少 `freq_token` 失败。
- 受影响实施暂停后，核对 granite-tsfm 0.3.9 的官方频率映射，主会话同步子设计与规范。修正仅从既有 `ContextBatch.freq`/`SegmentSet.freq` 补齐同设备 long token；OOV 显式告警、非法值和验证频率不一致明确拒绝。不改父公共协议、不换模型或检查点。
- prefix 小模型首次回归为 4 failed，修复后 TTM 专项为 10 passed。真实 TTM 仅复测失败项，退出 0：1 passed、2 deselected，23.62 s。已通过的 4 项未因 TTM 局部修改而重复执行。

| AC5 模型 | 实际 revision | 可训练 / 总参数 | 训练 / 总耗时 | 峰值分配显存 |
| --- | --- | --- | --- | --- |
| Chronos2 LoRA | `29ec3766d36d6f73f0696f85560a422f50e8498c` | 1,206,912 / 120,684,576（1.000055%） | 2.133 / 3.879 s | 962.235 MiB |
| TimesFM25 LoRA | `5a9806b9b291fad9233b5249d88263f1846304d3` | 2,457,600 / 233,746,880（1.051394%） | 1.138 / 2.695 s | 960.487 MiB |
| TTM head | `b972f0c22190b7502764526004d16e2b4ed39e8c` | 246,818 / 799,756（30.861663%） | 5.804 / 21.942 s | 24.114 MiB |

三项 AC5 均为 CUDA fp32、步骤 `[1,2,3,4,5]`；TTM head 不适用 LoRA 的 5% 阈值。两个真实 LoRA 的第 5 步损失未低于第 1 步，未宣称下降；AC4 的下降判定来自独立的 20 步随机小模型测试。

AC6：Chronos2 加载/预测合计 61.337 s，峰值分配显存 237.655 MiB；TimesFM25 合计 44.421 s，峰值 453.515 MiB。首轮加载时间包含下载与初始化。TTM 的 `load` 仅保存配置，复测首次 forecast 的 16.133 s 包含延迟加载，不将空 load 调用视为模型验收成功。

完整命令、逐项耗时、全部五步损失、库源码证据、首次失败与复测日志名见 `research/real-acceptance.md`。本机环境仍为 Python 3.13.11、torch 2.11.0+cu128、CUDA 12.8、驱动 617.14、RTX 5090 Laptop、24,463 MiB。

## 已知库语义限制

transformers 5.17.0 的 TimesFM 内置 quantile-loss 列索引与导出分位数映射存在差异，详见 `research/library-api-audit.md`。子设计要求使用库的 `forward(...).loss`，本任务保留该定义，未改写第三方损失，也未将源码差异记为验收失败。该限制不由测试通过消除。

## 数据保护

- 默认 pytest 只使用合成数据与随机小模型，不读取 `data/` 或 `ref/`，不下载真实权重，不依赖 GPU。
- 本机验收使用明确的 `weights` / `gpu` 标记。未执行、跳过与通过分别报告。
- `data/`、`ref/`、`runs/`、`cache/`、`*.log` 不进入 Git；`.trellis/workspace/` 保持跟踪。
- 验收文档仅包含汇总指标和必要元信息。

## 提交与归档授权

- 用户于 2026-09-29 确认按两组执行本地提交，并归档对应完成的 backbone-adapters。
- 两组工作提交为 `6f94aa2368152a7482f5e38b26c96355f895d1c4` 与 `c81d304ad26a39fbd0f11ff852b65870c9706206`；提交范围与已批准的 54 文件清单一致。
- 本次收尾只更新授权、提交记录及归档引用，未修改最终质量门禁之后的应用代码、测试或依赖；未重复训练或质量门禁。
- `task.py archive` 记录实际完成状态与日期；归档后的工作日志记录两组工作提交。父任务及其余三个子任务继续保留，不开始后续实施，不推送。
