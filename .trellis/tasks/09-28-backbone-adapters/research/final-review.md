# 最终全范围独立质量审查

日期：2026-09-29。分支：`codex/backbone-adapters`。HEAD：`3bb3a92`。范围：本子任务全部配置、协议、注册表、检查点、六个适配器、训练与缺失值工具、测试、依赖声明，以及相应规划和规范差异。

## 结论

最终全范围 trellis-check 通过。本轮未发现新增代码问题，无新增共享契约冲突。AC1–AC7 均有对应通过证据。最终独立离线检查为 125 passed、5 deselected、2 warnings。

本轮重新执行离线四项门禁，并核对步骤 7 的真实验收原始日志。真实模型行为在本轮未修改，因此没有重复已通过的权重或 GPU 验收。首次 TTM 失败及同一检查点修正后的复测继续分别保留。

## 已修复事项

本轮没有新增源码或测试修复。已复核前序修复及其回归：

- 步骤 6：验证通道顺序在参数更新前校验；模型及依赖加载失败转换为领域异常；TTM 保存初始选型 L/H 与 resolved revision，避免后续预测覆盖保存身份。详见 `step6-review.md`。
- 步骤 7：TTM prefix 检查点按已有频率字段生成官方频率 token，覆盖预测、训练及固定验证；映射频率、OOV、非法频率、词表越界、验证频率不一致均有实际随机模型回归。详见 `real-acceptance.md`。
- 前序测试断言没有放宽。默认测试没有新增 skip、xfail 或 warning filter。数据契约的 AST 与独立进程惰性导入检查保留。

## 未修复事项

- 已知第三方库限制：transformers 5.17.0 的 TimesFM 内置 quantile-loss 列索引与导出分位数映射存在差异。证据保留在 `library-api-audit.md`；当前子设计要求使用库的 `forward(...).loss`。本审查保留该定义，未修改第三方损失。若要改变损失定义，需要单独决定并同步共享契约。该限制未被标记为已消除。
- 没有新增阻塞本子任务验收的未决实现问题。提交、归档和推送不属于本审查操作；提交与归档分别等待用户确认，不推送。

## 契约与代码核对

- `load(cfg, fit_stats, *, reporter)` 与 `finetune(..., reporter, *, mode)` 在父设计、子设计、规范、实现与测试中一致。模式不复制到 `BackboneConfig` 或 `FinetuneConfig`。experiment-runner 只同步已批准的调用规划。
- 注册表包含 persistence、ridge、features、chronos2、timesfm25、ttm。新进程注册发现不导入 torch、chronos、transformers、tsfm_public、peft 或 sklearn；Options schema 可序列化，能力矩阵与实现对应。
- 检查点解析遵循 HF_ENDPOINT 与 HF_HUB_OFFLINE，暴露本地路径和实际 revision。TTM 分支选择先于快照解析；本地占位标识不写入 provenance。缺失依赖或检查点失败不会切换模型或训练模式。
- 基线数值、NaN、FitStats 缩放、窗口边界、种子抽样、验证通道顺序、固定验证窗口及最低验证损失权重恢复均有测试。数据层继续负责构造 fit 边界内的 SegmentSet。
- TimesFM、TTM 和 Chronos 使用真实库配置生成离线随机小模型，覆盖输出、NaN、20 步训练损失下降与权重往返。TTM 主干冻结检查保持逐元素相等。
- TTM 频率输入沿用 ContextBatch.freq 与 SegmentSet.freq。prefix token 为同设备、形状 `(B,)` 的 long 张量；非 prefix 模型不添加 token。OOV 保留库语义并报告 warning。

## 真实验收证据核对

已逐项核对 `cache/backbone-real-acceptance-first.log` 和 `cache/backbone-real-acceptance-ttm-retest1.log` 中的 JSON、pytest 结果和失败堆栈。汇总记录与原始日志一致。

| 验收 | 已核对结果 |
| --- | --- |
| AC5 Chronos2 | revision `29ec3766d36d6f73f0696f85560a422f50e8498c`；LoRA 1,206,912 / 120,684,576 = 1.000055%；5 个步骤和有限损失 |
| AC5 TimesFM25 | revision `5a9806b9b291fad9233b5249d88263f1846304d3`；LoRA 2,457,600 / 233,746,880 = 1.051394%；5 个步骤和有限损失 |
| AC5 TTM | 分支 `512-48-ft-r2.1`；revision `b972f0c22190b7502764526004d16e2b4ed39e8c`；head 246,818 / 799,756；5 个步骤和有限损失 |
| AC6 | Chronos2 和 TimesFM25 参数实际位于 cuda:0，dtype 为 torch.bfloat16；零样本输出形状正确且有限 |
| AC7 | 依赖记录及真实 gpu 测试共同确认 CUDA 可用，capability 为 `(12, 0)`；torch 2.11.0+cu128，CUDA runtime 12.8 |

首轮真实验收为 4 passed、1 failed、121 deselected，121.79 s。TTM 因缺少 freq_token 首次失败；定向复测为 1 passed、2 deselected，23.62 s。检查点和阈值没有改变。

三个模型的加载、预测、训练耗时及峰值分配显存已与 `verification.md` 和 `real-acceptance.md` 核对。TTM 的首次 forecast 包含延迟加载；文档没有把空 load 调用记作模型加载通过。两项真实 LoRA 的首末五步损失未下降，记录明确区分 AC5 的五步要求和 AC4 的独立二十步下降断言。

## 最终独立离线命令

命令环境为 `UV_OFFLINE=true`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`。测试使用合成数据与临时目录中的随机小模型，不读取 data/ 或 ref/，不依赖实际权重或 GPU。

| 命令 | 结果 | 命令耗时 |
| --- | --- | --- |
| `uv run ruff check` | exit 0；All checks passed | 0.177 s |
| `uv run ruff format --check` | exit 0；57 files already formatted | 0.165 s |
| `uv run pyright` | exit 0；0 errors、0 warnings、0 informations | 11.247 s |
| `uv run pytest` | exit 0；125 passed、5 deselected、2 warnings；pytest 12.30 s | 14.475 s |

两条 warning 来自 Chronos 在有 CUDA 的机器上执行 CPU 小模型训练的库提示，未过滤。日志分别为已忽略的 `cache/backbone-final-review-ruff.log`、`cache/backbone-final-review-format.log`、`cache/backbone-final-review-pyright.log` 和 `cache/backbone-final-review-pytest.log`。

补充检查：`uv lock --check --offline` exit 0，Resolved 101 packages；`git diff --check` exit 0，只有现有 LF/CRLF 提示。没有手工修改锁文件或重复安装依赖。

## 规范、范围与 Git 边界

- Phase 3.3 已核对：本次修改的 7 份 backend 规范文件（含索引）引用实际实现与测试路径。Verified 仅覆盖已实现的 data-contract 和 backbone-adapters 范围；运行器、服务、界面及评价指标仍为 Decided。
- implement.jsonl 的 13 个引用和 check.jsonl 的 10 个引用均存在；task.json 可解析且任务仍为 in_progress。未开始后续子任务实现。
- 当前分支为 codex/backbone-adapters，HEAD 为 3bb3a92，索引为空。本报告写入前共有 53 个改动候选；加入本报告后为 54 个，与提交方案对应。
- data/、ref/、runs/、cache/ 与 `*.log` 被忽略，没有出现在候选清单中。`.trellis/workspace/` 的 3 个原有文件仍被跟踪，且未被忽略。未发现候选源码或测试读取私有目录。
- 未加入 TimesFM-3 或 momentfm；未发现运行器、服务、评价或 web 实现候选。数据契约实现文件未被修改。
- 依赖提交仅包含 pyproject.toml 与 uv.lock；其余功能、测试及证据另成提交。提交方案已草拟，实际提交与 task.py archive 的自动提交仍分别需要用户确认。

本审查只新增本报告，未 commit、archive 或 push。报告完成后释放源码、测试和本报告的编辑所有权，交由主会话更新最终状态与提交方案。
