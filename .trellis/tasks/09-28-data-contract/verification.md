# 数据契约实施与验收记录

## 范围与状态

- 基线提交：`9e1904d`。开始时工作区干净。
- 活动任务：`09-28-data-contract`；分支：`codex/data-contract`。
- 已执行 `python ./.trellis/scripts/task.py start 09-28-data-contract`。
- 本记录只覆盖 data-contract。父设计未修改，其他子任务未开始。
- 步骤 1–10 与最终全范围审查完成；用户批准基准修正后，AC1–AC6 全部通过。Phase 3.3 与 Phase 3.4 已完成，功能提交为 `04bd695`。用户已要求完成当前任务收尾，归档随后由 task.py archive 执行。

## 已批准的设计修正

父设计 3.1 定义 `channels: null` 自动选择数值列。子设计原先选择除时间列外的所有列。用户确认后，子设计第 2 节和实施步骤 3 已同步修正。自动识别检查完整列的非空值；全空列保留为可空浮点通道；字符串标识列忽略；显式配置的通道严格转换并使用脱敏错误。

## 步骤记录

| 步骤 | 状态 | 证据 |
| --- | --- | --- |
| 1 工具链 | 已完成 | `uv sync`、`uv run tsllm --help` 均退出 0；Python 3.13.11 |
| 2–3 配置、读取与注册 | 已完成 | 18 项合成测试通过，含完整异常链的脱敏检查 |
| 4–5 重采样、分段与划分 | 已完成 | 累计 35 项测试通过；含右端点、observed、max_gap、min_length 与有效点划分 |
| 6–7 缓存、统计与窗口标签 | 已完成 | `pytest` 71 passed；Ruff check 通过；format 30 files already formatted；pyright 0 errors |
| 步骤 7 审查门禁 | 已通过 | 独立 trellis-check；78 tests passed；8 类约束变异全部检出 |
| 8–9 CLI 与配置 | 已完成 | 新增 8 项合成测试；四项命令通过，pytest 86 passed |
| 10 AC4 本机入库 | 已通过 | 523,782 有效分钟；批准基准 523,702；偏差 +0.015276%，旧基准失败证据保留 |
| 10 AC5 本机入库 | 已通过 | 17,420 有效点等于独立 CSV 核对的非全空行数 |
| 最终完整质量检查 | 已通过 | 独立 trellis-check 覆盖全部 data-contract 改动；四项命令退出 0，pytest 87 passed |
| Phase 3.3 | 已完成 | 六项适用后端规范标记 Verified，引用实际实现与测试路径；后续模块保留 Decided |
| Phase 3.4 | 已完成 | 用户批准后创建本地提交 `04bd695`；49 个文件与批准方案一致 |

步骤 9 后命令摘要：`uv run ruff check` 无诊断；`uv run ruff format --check` 为 `32 files already formatted`；`uv run pyright` 为 `0 errors, 0 warnings, 0 informations`；`uv run pytest` 为 `86 passed`。全部退出 0。

AC4 首次完整入库的 CLI 内计时为 3.138 s，进程墙钟耗时为 3.805 s；43 个保留段。首次按旧基准 460,417 验收失败后暂停。独立标准库 CSV 核对与数据层读取均得到去重后有效行 3,142,209；研究资料基准差异来源原因未查明。用户随后批准以原始有效行 3,142,212 ÷ 6 = 523,702 为基准，保留 ±2% 容差。父研究记录、子任务 AC4 与对应 spec 已同步，父共享设计和数据处理规则未改动。

AC5 首次完整入库的 CLI 内计时为 0.038 s，进程墙钟耗时为 0.558 s；17,420 个有效点、1 个段。独立标准库 CSV 核对得到 17,420 个非全空源行。两次验收的计数、源指纹、各划分边界和历史失败证据均保存在 `prd.md`。

### 最终全范围审查与复测

独立 trellis-check 发现：缓存写入返回后，仅比较返回元数据中的源指纹，不能检出元数据构造后发生的源变化。新增 `after_write_cache` 回归用例在修正前得到 **2 passed, 1 failed**，失败为 `DID NOT RAISE DatasetConfigError`。实现现已在写入后重新读取源文件指纹，发现变化时删除 `meta.json` 完成标记并抛出域异常。该修正未改变父共享契约。

最终命令输出摘要如下，全部退出 0：

| 命令 | 输出摘要 |
| --- | --- |
| `uv run ruff check` | 无诊断 |
| `uv run ruff format --check` | `32 files already formatted` |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `uv run pytest` | `87 passed` |

Ruff 文件发现覆盖全部 **30 个 src/tests Python 文件**。格式检查的 32 个文件保留工具原始输出口径。此前 86 项测试与早期不完整 Ruff 检查记录均保留，最终门禁使用本节结果。

最终源指纹修正后，对两个真实数据集执行 `uv run tsllm data ingest <id> --force`，均退出 0，完整执行读取、重采样、分段、划分与缓存写入：

| 数据集 | CLI 内耗时 | 进程墙钟耗时 | 有效点数 | 保留段数 |
| --- | ---: | ---: | ---: | ---: |
| yangquan_kiln | 4.535 s | 6.763 s | 523,782 分钟 | 43 |
| ETTh1 | 0.060 s | 0.827 s | 17,420 | 1 |

写后核对：两个缓存均为 fresh；源指纹、配置哈希、计数与划分边界不变；各划分计数与总数一致。AC4 相对批准基准 523,702 的偏差为 **+0.015276%**，满足 ±2%。后续改动仅同步文档，不改变本次验证的代码。

### Phase 3.3 规范同步

`directory-structure.md`、`database-guidelines.md`、`error-handling.md`、`logging-guidelines.md`、`quality-guidelines.md`、`time-series-guidelines.md` 及后端索引已更新。Verified 仅覆盖 config、data、errors、reporting、数据 CLI 和对应测试。模型适配器、运行器、服务、前端与指标计算继续保留规划状态。

规范记录了全列数值识别、数字时间文本解析、配置与解析错误脱敏、缓存写后源指纹复核、根目录忽略规则、未来标签端点及有效拟合行限制。存储规范包含七节可执行契约和真实测试引用。`AGENTS.md` 的实现状态已同步；父 `design.md` 未修改。

## 数据保护

- 测试使用合成数据。真实数据验收独立执行。
- `data/`、`ref/`、`runs/`、`cache/` 不加入 Git。
- 功能已提交为 `04bd695`。用户已要求完成收尾，允许归档本任务；不推送。
- `.trellis/workspace/` 保持跟踪。误加的目录忽略规则与取消跟踪操作已撤销；仅 `*.log` 诊断日志和既有运行态路径保持忽略。

## 工具链检查范围修正

首次完整 Ruff 命令检查到 `.trellis` 中既有生成脚本和规划 Markdown 的 170 个 lint 问题、23 个格式问题。Ruff 使用 `extend-exclude = [".trellis"]` 排除生成工具与规划材料，应用与测试规则保持不变。

原 `.gitignore` 的 `data/` 同时忽略了 `src/tsllm/data` 与 `tests/data`，导致早期 Ruff 只检查 13 个文件。该结果不作为完整门禁证据。规则已改为根目录锚定的 `/data/`、`/ref/`、`/runs/`、`/cache/`。修正后重新通过四项检查，格式检查覆盖 30 个 Python 文件。`git check-ignore --no-index --verbose` 确认私有根目录命中，数据层源码和测试未命中。

## AC2、AC3、AC6 测试对应

| 验收行为 | 测试位置 |
| --- | --- |
| 晚出现数值、自动数值识别、去重、编码、脱敏 | `tests/data/test_source.py` |
| 因果右端点、网格补齐、observed、native grid | `tests/data/test_prepare.py` |
| max_gap、min_length、按有效点划分、规则组合 | `tests/data/test_rules_splits.py` |
| 缓存往返、哈希、文件大小或 mtime 变化过期 | `tests/data/test_cache.py` |
| fit-only 统计、目标划分、段边界、前一划分上下文、批次掩码 | `tests/data/test_stats_windows.py` |
| fit-only 阈值、未来窗口、连续 min_duration、null 中断 | `tests/data/test_labels.py` |
| 合成数据生成 | `tests/conftest.py`；测试运行时仅使用临时文件与内存数组 |
| 不导入模型库 | `tests/data/test_stats_windows.py` 的 AST 与独立进程导入测试 |

## 步骤 7 审查发现

1. 显式配置通道时，CSV 的纯数字时间文本会被推断为整数，导致合法的 `time_format` 配置被拒绝。回归测试先复现失败，再将时间列固定按 String 读取后解析。
2. 原有标签测试未能检出窗口由 `[o+1, o+W]` 错移为 `[o, o+W-1]` 的变异。已增加 5 个精确边界用例；标签实现原本使用正确的未来窗口。

变异检查使用隔离源副本，并断言被测模块的 `__file__` 指向副本。只有断言失败或预期异常未抛出才计为检出；导入或语法错误不计。8 类变异结果如下。检查完成后正常源代码的四项命令全部通过：Ruff 无诊断、format 30 files already formatted、pyright 0 errors、pytest 78 passed。独立审查确认 Ruff 覆盖全部 28 个应用/测试 Python 文件，`.trellis` 不在输入中。格式检查文件数保留命令的原始输出口径。

| 删除或修改的约束 | 检出测试 | 断言失败数 |
| --- | --- | ---: |
| 统计与阈值 fit-only | `test_fit_statistics_ignore_future`、`test_threshold_ignores_future`，各 3 个划分 | 6 |
| 统计与阈值 eligible-only | `test_stats_ignore_ineligible_fit_rows`、`test_threshold_ignores_ineligible_fit` | 2 |
| 训练目标 fit 限制 | `test_train_targets_stay_fit_and_windows_stay_in_one_segment` | 1 |
| 评价目标所属划分限制 | `test_eval_targets_stay_in_split`，3 个划分 | 3 |
| 窗口清单同段限制 | `test_train_targets_stay_fit_and_windows_stay_in_one_segment` | 1 |
| 批次与标签提取同段限制 | `test_invalid_extraction_rejected`、`test_illegal_label_window_rejected` | 2 |
| 标签切片向前偏移一行 | 精确边界用例：起点与目标末行 | 2 |
| 标签切片包含起点 | 精确边界用例：起点 | 1 |

## Phase 3.4 提交方案（历史记录，已批准执行）

建议按一项完整功能提交：数据契约实现、测试、工具链、数据集 YAML、已批准的设计和基准修正、规范及验收记录共同构成 AC1–AC6。将这些文件合为一个提交，可独立验证和撤回。父共享设计未修改。

提出方案时分支为 `codex/data-contract`，HEAD 为 `9e1904d`，暂存区为空。49 个候选文件全部来自本任务；未发现来源不明的改动。候选文件均为 UTF-8 文本，最大文件为 `uv.lock`（72,953 bytes）。根目录 `data/`、`ref/`、`runs/`、`cache/` 不在候选范围。

用户已批准下列精确文件集合，已通过本地 `git commit -F` 创建 `04bd695`。提交后工作区干净，私有目录未被跟踪。用户后续要求在本次对话完成行政收尾；不推送，不开始下一子任务。

提交信息使用中文；沿用仓库无 emoji 的格式；标题不含 `[AI]`。包含 Why 和 Tested，以及 Agent-Task、Agent-Model、Generated-By 结构化尾注。提交信息由 git-commit 技能的 compose_commit_message.ps1 生成。

### 完整提交信息

```text
feat(data): 实现数据契约与数据集入库

Why: 为时序实验建立可复用且防止数据泄漏的数据基础
实现配置注册、重采样、分段、时序划分、缓存、窗口和规则标签
增加数据 CLI、合成测试，并同步已验证规范与批准的验收基准

Tested: ruff check; ruff format --check; pyright; pytest (87 passed); AC4 and AC5 local ingestion
Agent-Task: 09-28-data-contract
Agent-Model: gpt-6
Generated-By: agent
```

### 候选文件

`M` 为已跟踪文件的未暂存改动，`??` 为未跟踪文件。下列状态保留方案提出时的快照；文件现已全部进入功能提交。

```text
 M .gitignore
 M .trellis/spec/backend/database-guidelines.md
 M .trellis/spec/backend/directory-structure.md
 M .trellis/spec/backend/error-handling.md
 M .trellis/spec/backend/index.md
 M .trellis/spec/backend/logging-guidelines.md
 M .trellis/spec/backend/quality-guidelines.md
 M .trellis/spec/backend/time-series-guidelines.md
 M .trellis/tasks/09-28-data-contract/design.md
 M .trellis/tasks/09-28-data-contract/implement.md
 M .trellis/tasks/09-28-data-contract/prd.md
 M .trellis/tasks/09-28-data-contract/task.json
 M .trellis/tasks/09-28-tsfm-platform/research/data-profile.md
 M AGENTS.md
 M pyproject.toml
 M src/tsllm/__init__.py
?? .trellis/tasks/09-28-data-contract/verification.md
?? configs/datasets/ETTh1.yaml
?? configs/datasets/yangquan_kiln.yaml
?? src/tsllm/cli.py
?? src/tsllm/config/__init__.py
?? src/tsllm/config/base.py
?? src/tsllm/config/dataset.py
?? src/tsllm/config/io.py
?? src/tsllm/config/labels.py
?? src/tsllm/data/__init__.py
?? src/tsllm/data/cache.py
?? src/tsllm/data/labels.py
?? src/tsllm/data/prepare.py
?? src/tsllm/data/profile.py
?? src/tsllm/data/registry.py
?? src/tsllm/data/rules.py
?? src/tsllm/data/source.py
?? src/tsllm/data/stats.py
?? src/tsllm/data/types.py
?? src/tsllm/data/windows.py
?? src/tsllm/errors.py
?? src/tsllm/reporting.py
?? tests/config/test_dataset.py
?? tests/conftest.py
?? tests/data/test_cache.py
?? tests/data/test_ingest.py
?? tests/data/test_labels.py
?? tests/data/test_prepare.py
?? tests/data/test_rules_splits.py
?? tests/data/test_source.py
?? tests/data/test_stats_windows.py
?? tests/test_cli.py
?? uv.lock
```

### 文档收尾检查

- 已核对六项 Verified 规范中的 27 个实际源码和测试路径；规划中的 metrics 路径保留规划状态。
- 存储规范已包含七节契约；task.json 可解析，任务状态继续为 in_progress。
- git diff --check 通过；行尾提示仅表示 Git 后续会按当前设置转换为 CRLF。
- 未修改最终质量门禁与本机复测之后的应用代码、测试或依赖。
