# 下一任务规划：独立证据预审

日期：2026-09-30（America/Chicago）。审查角色：`/root/independent_review`。

## 0. 范围与上下文

本轮为单任务证据预审。范围为 `.trellis/tasks/09-30-next-task-planning/`，任务数 1，状态 `planning`，children/subtasks 均为空。当前尚未确认产品方向，本轮不对完整方案作通过判断，也不把缺少 `design.md`、`implement.md` 记为预审缺陷。

只读 Git 查询确认 HEAD 为 `945a76ecf35303083aec36acd5e879a3aa409aba`，分支为 `codex/frontend-route-lazy-loading`。`git diff --name-only 934ba580e39a3ecee53abe936cc41ff5aaef0049 HEAD -- web src configs pyproject.toml uv.lock`、这些产品路径的工作树 diff 和 `git diff --cached --name-only` 均为空。检查时完整 `git status --porcelain -uall` 仅列出本规划任务内的未跟踪材料。该结果不证明当前运行时重新通过验收。

未收到可识别的原生 `SubagentStart` 文件正文或 `Full hook output saved to` 路径，采用子代理显式补读。已读根 `AGENTS.md`、任务 `task.json`、真实 `check.jsonl` 的三条引用、现有 `prd.md`、workflow 规划与 2.1/2.2。仓库根没有 `CONTEXT.md`；对 `.trellis/`、`src/`、`web/` 的 `AGENTS.md`/`CONTEXT.md` 文件搜索无匹配。本代理未重新证明主会话创建前状态、任务创建调用或其他会话的任务指针。

已读取 `C:/Users/lyh/.agents/skills/trellis-plan-review/SKILL.md`，采用断言核对、事实与推论分离、AC 逐子句追踪和证据边界规则。用户限定报告路径覆盖技能默认路径，未运行会写 `.trellis/reviews/` 的 helper。未运行完整方案机械预检或产品门槛。

指定八份文件均按实际行号补读全文；初始批量输出截断的内容未当作完整阅读证明：

| 文件 | 已读范围 | 材料层级 |
| --- | --- | --- |
| `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md` | 1–295 | 父需求、用户决定与历史验收 |
| `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md` | 1–374 | 共享契约 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md` | 1–394，分两段 | recovery-r1 历史评估 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/verification.md` | 1–62 | 旧评估验收时点 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md` | 1–53 | 后续提交归档与证据复核 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/independent/final-review.md` | 1–87 | 后续独立终审 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md` | 1–109 | B1 正式实施的另一组观测 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md` | 1–96 | B1 冻结修订验收 |

另外全文读取 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/README.md:1-41` 与 `result.md:1-15`；解析该目录的 archive-receipt、postarchive-validation、precommit、log-preservation、receipt-launcher-failure、stage-byte-check-1、stage-whitespace-check-1。读取历史回执不等于重跑其中命令。

## 1. 预审结论

证据预审完成：未解决的范围内发现为 0；已修正的引用定位提示为 1。主会话 `research/archive-evidence.md` 的主要事实、版本分层和结论边界与指定材料一致。该结论支持继续候选收敛，不表示完整规划可执行。

当前证据支持保留 B1。指定旧问题中的前端拆分实施、旧评估收尾及对比警告已有后续完成记录，不能再次当作当前未完成项。历史体积警告、首次页面较慢数值和未实现功能列表均不足以单独决定下一产品任务。

`past_covariate` 的父需求/共享设计差异可确认。已搜索的历史材料中未找到专门解决该差异的明确用户决定或同步记录。现有拒绝行为、原始范围排除与“共享设计优先”同时存在，候选若依赖该差异，须先确定需求与权威文档的处理方式。

## 2. 发现与已修正记录

当前未解决 findings 列表为空。没有证据支持新增产品缺陷或完整方案阻断项。

### EPR-01：命令来源行号未覆盖后端命令（提示，已修正）

- 违反要求：本任务 R1/R2 要求事实及 `path:line` 可核实，见 `.trellis/tasks/09-30-next-task-planning/prd.md:24-25`。
- 原位置与断言：`.trellis/tasks/09-30-next-task-planning/research/archive-evidence.md:48` 原引用 `AGENTS.md:36-50`，用于支持后端四命令与前端三门槛。
- 事实：后端四命令实际在 `AGENTS.md:31-34`，前端三门槛在 `AGENTS.md:39-41`。原范围未覆盖后端四命令。
- 影响：读者无法在原范围核对全部命令。命令内容正确，未影响候选方向或产品状态结论。
- 最小修订建议与结果：只更正来源行号。主会话已完成，本代理重新读取第 48 行确认采用两个正确范围。本代理未改该文件。

## 3. 主会话证据清单核对

| 主会话条目 | 独立核对与来源 | 解释边界 |
| --- | --- | --- |
| F1、F2 | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:99-117`、`:243-266`、`:290-295` 记录 AC1–AC7 完成及用户取消整机断网条件。 | 本轮未读取真实运行或缓存，未重跑父验收；被取消的条件不构成尚欠任务。 |
| F3 | `web/src/router.tsx:12-57` 有七条 lazy 路由；`:2`、`:8-9` 保留同步布局和初始 fallback。`web/src/components/AppLayout.tsx:19-58` 处理导航等待；`web/src/components/RouteLoading.tsx:9-38` 保留 URL 并阻止默认导航后调用 reload。 | 当前静态源码事实，未作本轮可见验收。 |
| F4 | `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:7-13`、`:298-322`、`:379-394` 支持 90 个主观测、3 个补充流程、B1 建议及 B2 不建议采用。 | 225.0 ms 属于旧评估；实际使用频率未测，B2 高值原因未查明。 |
| F5 | `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md:13-34`、`:91-99` 支持 60 个主观测、2 个完整流程、234.0 ms、首次使用增加 20.1–33.6 ms。 | 两个实验分别保留统计组别，不混算，不解释为本轮新测量。 |
| F6、F7 | `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/result.md:5-12` 和该目录 `archive-receipt.json:2-17` 记录 B1 工作提交 `934ba580e39a3ecee53abe936cc41ff5aaef0049`、归档 `40648784376a5d3dc165e75f2aa981f9843722c4`。`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md:9-19` 记录旧评估工作提交 `967644734806d9056af67fcc7c284d5147b9f97e`、归档 `60fc52f7b46b205181b2c83f697b3b2628bfca18`。 | 原报告未提交/未归档说明属于采集时点，后续 closure 已完成对应工作。 |
| F8 | `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/README.md:37-41` 与回执一致：295 个文件字节匹配，完整检查退出 2，18 个原证据路径有空白告警，其他 277 个文件退出 0。`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/independent/final-review.md:37-67` 保留该轮首次工具失败与实际退出 0。 | 两轮检查范围与时点不同，不互相覆盖。历史失败不自动成为当前产品失败。 |
| F9 | `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:75-91`、`:302`、`:381-383` 与 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md:36-59`、`:91-98` 区分正文、离线 gzip、transfer、FCP 与功能就绪。 | 体积警告或压缩估算不能单独推出新产品缺陷与收益。 |
| F10 | `.trellis/tasks/archive/2026-09/09-29-compare-warnings/prd.md:68-77`、`:93-95` 记录对应后续实施、验收与归档。 | 父 PRD 尾部旧遗留项不等于当前缺陷清单；未重跑该功能验收。 |

冻结路径映射使用 `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/preparation/reference-adapters/mapping.closure-v1.json`。四份 manifest 定义从该文件第 8、114、220、334 行起；adapter 路径在第 11、117、223、337 行。独立只读核对得到 12、12、13、13 条，共 50 条目标全部存在，四份 adapter 的 SHA-256 和大小均匹配。两个 B1 adapter 各有 5 条改写后的旧评估引用。未修改冻结原件或读取旧临时目录。

## 4. past_covariate：事实、未验证和用户决策

### 已确认

1. `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:84` 把过去与未来已知协变量输入都排除，允许字典标注，运行时报未实现。
2. `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:89` 写预测使用 target 与 past_covariate，只把 known_future_covariate 写为未实现。
3. 定向 `git blame` 显示这两行均来自 `1e64b502`，时间为 2026-09-28 10:16:41 -0500。不能用其中一个是后续改动解释差异。
4. `.trellis/tasks/archive/2026-09/09-28-experiment-runner/design.md:57` 明确输入只含 target，past_covariate 抛 NotImplementedError；该处没有用户裁决或父共享契约已同步记录。
5. `src/tsllm/tasks/validation.py:22-26` 拒绝所有 known_future_covariate，再拒绝 forecast 中的 past_covariate。`tests/service/test_api_basic.py:102-112` 构造 target 与 past_covariate 混合通道，断言 API 422/NOT_IMPLEMENTED，拒绝提交不新增运行目录。这里只确认源码与断言存在，未执行测试。
6. `.trellis/spec/backend/error-handling.md:37`、`:121` 将 past_covariate 作为未实现示例；`.trellis/spec/backend/index.md:17`、`:54` 同时声明父 design 为共享契约且优先于规范。父设计 `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:3` 要求共享契约变更先同步。

### 未验证

对 `.trellis/tasks/archive/2026-09/`、`.trellis/spec/`、`.trellis/workspace/` 的定向搜索使用 past_covariate、past covariates、过去协变量及协变量/未实现组合；对 `.trellis/tasks/`、`.trellis/spec/`、`src/tsllm/tasks/validation.py` 执行相关字符串的只读 `git log -G`，补读 runner 设计与偏差记录。在该范围内未找到明确解决此差异的用户决定或父设计同步记录。不能据此断言未纳入范围的全部对话都没有该决定。

父任务 AC1–AC7 完成没有单独证明该差异已经裁决。实现与测试说明拒绝路径已建立，不能单独证明共享设计的相反文字已被授权废止。

### 需要用户决定的边界

本轮保持现有行为。若候选涉及协变量，需要明确目标是统一历史文档对当前能力的说明，还是批准新增输入能力。两种选择的范围、负责层和验收成本不同。修改归档共享契约或旧任务原件也不在本轮授权内。

“实现 past_covariate 一定是当前缺陷修复”“必须新增协变量支持才能保留 B1”“父任务完成说明差异已解决”均缺少现有证据支持。主会话当前清单没有作这些推断，应保留条件性表述。

## 5. 后续最小验收机制的检查点

以下为下一轮必要输入，不是已确认 findings，也不是修订后的完整方案。

- 候选依据：每个候选须有可定位的未满足行为与用户价值；允许维持现状。当前完整指定材料未证明必须新增 B2、传输优化或再次收尾。依据为 `.trellis/tasks/09-30-next-task-planning/prd.md:9`、`:25`、`:34`，以及 `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:302-322`。
- 契约决策：若选择协变量相关方向，先记录用户选择与权威文件的授权范围。不得先实施再用测试结果替代决定。依据为 `.trellis/tasks/09-30-next-task-planning/prd.md:27`、`:37`、`:54` 与父共享设计第 3、89 行。
- AC 逐子句：方向确认后，每个子句分别映射需求、设计机制、执行步骤与证据；不能用总体“检查通过”覆盖未验证子句。依据为 `.trellis/tasks/09-30-next-task-planning/prd.md:27-28`、`:42-47` 和 `.trellis/workflow.md:163-167`。
- 验证边界：如影响加载或图表，静态阅读与 jsdom 不足以证明真实 Canvas、缺块恢复和 query/hash；获准后须保留同修订、合成隔离环境及真实交互证据。纯文档候选无需默认扩成性能矩阵。依据为 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md:69-78`。
- 失败与回滚：保留首次失败与同修订复测，明确定向回滚范围，不撤销其他作者改动。依据为 `.trellis/tasks/09-30-next-task-planning/prd.md:28`、`:38` 和 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/README.md:37-41`。
- 最终审查：方向确认后才评价完整方案，末轮再核对清单引用、完整 status 和实际写入范围。材料检查不替代产品验收，不运行 start。依据为 `.trellis/tasks/09-30-next-task-planning/prd.md:29`、`:33-38`、`:43-47` 与 `.trellis/workflow.md:159`、`:205-207`。

现有规划 AC1/AC2 所需候选尚在研究流程；本代理没有把半写候选作为最终裁决依据。AC3 依赖方向确认；AC4 需要后续完整独立审查；AC5/AC6 需要最终材料和状态。上述阶段依赖不计为预审缺陷。

## 6. 操作边界与限制

未运行测试、构建、服务、浏览器验收、性能实验、真实实验、训练、入库、作业提交、权重下载、安装升级、网络或防火墙操作。未读取私有根 data/、ref/、runs/、cache/ 或备份内容。没有创建任务、start、提交、暂存、归档、amend、push、发布、创建 Goal 或递归派发。唯一写入为本报告。第一次报告工具调用在 JavaScript 解析阶段报 SyntaxError，没有执行文件写入；修正调用后写入。

可保留当前 B1、两组历史实验的版本分层、首次失败及修订结果、既有冻结路径映射，以及不先行认定协变量为产品缺陷的限定。

代理审查与主会话共享模型和上下文限制。无未解决 finding 仅表示本次预审未发现其他可证实问题，不表示完整规划已获批准。
