# 下一任务规划：独立候选审查

日期：2026-09-30（America/Chicago）。审查角色：`/root/independent_review`。范围：单任务 `.trellis/tasks/09-30-next-task-planning/`，状态 `planning`。

## 1. 结论

候选材料可以用于用户选择方向。候选选择阻塞 0 项；需用户决定 1 项；非阻塞成稿建议 3 项。没有完整设计或实施步骤，本轮不作完整方案通过结论。

候选一有可定位的契约差异和配置说明改进机会。候选一的用户收益属于合理推断，尚无实际误配置、返工频率或耗时证据。当前证据足以提出有条件的配置说明改进选项，尚不足以把该选项描述为必须修复的产品故障或证明其优先级高于其他用户需求。候选二有充分依据，可以保持现有产品并保留未决差异记录。

研究报告已经把收益假设与事实分开，并明确允许维持现状，因此未将缺少 UI 说明过度认定为运行实现缺陷。见 `.trellis/tasks/09-30-next-task-planning/research/current-state-candidates.md:12-16`、`:95`、`:145-149`。建议主会话继续使用该限定。

## 2. 审查对象与实际操作

全文读取 `.trellis/tasks/09-30-next-task-planning/research/current-state-candidates.md:1-149`，读取时 SHA-256 为 `7c3f7f1090d2829b2a8a7de02ba0f3b142c7c1564a3878d694236a692501517c`。复用本代理已完成的八份必读报告、B1 closure、路径映射和历史决定核对，未重复读原始观测或进行全库审计。前轮结果在 `.trellis/tasks/09-30-next-task-planning/research/independent-evidence-review.md`。

新增核对限定在通道配置 UI、保存/提交调用链、预测与分类输入、Pydantic/OpenAPI/生成类型及直接相关规范。只读 Git 查询仍显示 HEAD `945a76ecf35303083aec36acd5e879a3aa409aba`、分支 `codex/frontend-route-lazy-loading`；完整 status 中的改动均为本规划任务材料。主会话另行复核的任务指针作为派发上下文，本代理未写指针或状态。

上下文采用本轮派发与显式文件读取；继续使用已加载的 `trellis-plan-review` 方法。没有收到新的原生 hook 全文或补读路径。首次并行输出中的截断源码已经以小范围读取补齐；不把截断输出视为完整证据。

## 3. 两个候选的事实核对

| 项目 | 独立结果 | 直接证据 |
| --- | --- | --- |
| 角色可选择、缺少任务适用说明 | 四个角色选项存在。编辑处没有预测/分类适用说明；已有 Alert 只解释入库状态。该缺少说明是可确认的页面事实，尚不是已证实的用户故障。 | `web/src/pages/DatasetDetailPage.tsx:28-34`、`web/src/pages/DatasetDetailPage.tsx:73-83`、`web/src/pages/DatasetDetailPage.tsx:104-164`。全文件针对协变量、未实现、forecast、classify 的搜索只有两个角色标签。 |
| 保存不等于实验可执行 | 更新通道会验证数据集配置并保存 YAML；保存接口不调用 validate_job。正常角色标注保存与实验拒绝可以同时成立。 | `src/tsllm/data/channels.py:21-42`；`src/tsllm/service/routes/datasets.py:75-84`。 |
| 预览不验证数据集角色能力 | 预览校验 RunConfig schema 后直接设置 preview，最终提交再处理服务错误。RunConfig 的 dataset 是 id 字符串，不嵌入 DatasetConfig 通道。 | `web/src/pages/RunNewPage.tsx:75-102`；`src/tsllm/config/run.py:93-103`；`src/tsllm/config/schema.py:8-14`。 |
| 预测提交拒绝两类协变量 | known_future_covariate 先被拒绝；forecast 中的 past_covariate 随后被拒绝。服务调用 validate_job 后才调用 jobs.submit。 | `src/tsllm/tasks/validation.py:17-44`；`src/tsllm/service/routes/runs.py:26-35`。 |
| 拒绝的 HTTP 及目录副作用 | NotImplementedError 映射 422/NOT_IMPLEMENTED；现有服务测试断言 mixed target/past_covariate 拒绝且拒绝提交不新增运行目录。 | `src/tsllm/service/errors.py:66-67`、`src/tsllm/service/errors.py:95-98`；`tests/service/test_api_basic.py:102-112`。仅检查测试源码，未执行。 |
| 分类过去协变量边界 | classify 不经过 forecast 专用的过去协变量拒绝分支；数据读取保留非 ignore 通道，分类表示提取使用这些通道的 context_batch。只能表述该角色不因 forecast 专用规则被拒绝；能力、缓存和其他合法性条件仍适用。 | `src/tsllm/tasks/validation.py:22-44`；`src/tsllm/data/source.py:17-20`；`src/tsllm/data/windows.py:101-112`；`src/tsllm/tasks/classify.py:31-47`。 |
| 分类未来协变量边界 | known_future_covariate 的拒绝条件没有 task 类型限制，覆盖分类实验。不能在 UI 声称只有预测不支持该角色。 | `src/tsllm/tasks/validation.py:22-26`。 |
| 不能直接删除预测拒绝 | context_batch、targets、segment_set 均使用 prepared.channels；forecast 的指标与写出通道也使用该列表。仅删拒绝会让过去协变量进入预测目标和评价通道。该结论为静态调用链推断。 | `src/tsllm/data/windows.py:101-137`；`src/tsllm/tasks/forecast.py:50-55`、`src/tsllm/tasks/forecast.py:94-120`。 |
| CLI 与 worker 的边界 | `--ingest` 可先执行入库；worker 对既有运行目录先写 running/env，再进入实验校验。研究报告没有把服务提交的“不建目录”推广为所有入口零副作用。 | `src/tsllm/cli.py:140-156`；`src/tsllm/runs/worker.py:39-74`。 |
| 配置哈希 | 哈希使用实例 model_dump，并把通道投影为 name/role。修改 Field 的 schema 描述不要求改变哈希算法或实例角色值。 | `src/tsllm/data/cache.py:24-29`。 |

研究报告第 5 节的定位和主要推断与上述源码一致。分类过去协变量尚无本轮新增运行验收，应保留 `.trellis/tasks/09-30-next-task-planning/research/current-state-candidates.md:88` 的未验收限定。

候选二的依据继续成立：B1 工作提交/归档和旧评估收尾已有记录；前轮审查已确认指定产品树保持 B1。依据为 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/result.md:5-12` 与 `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md:53`。保留现状没有新增产品兼容风险，但未决契约差异仍需保留。

## 4. 共享契约与最高价值用户决定

历史冲突保持前轮结论：父 PRD `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:84` 排除两种协变量输入；父共享设计 `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:89` 写预测使用 target 与 past_covariate；runner `.trellis/tasks/archive/2026-09/09-28-experiment-runner/design.md:57` 再次写预测过去协变量未实现。前轮定向 git blame 证明父两处文字同源于初始规划提交，在已搜索范围内未找到专门解决该差异的用户决定。

现有代码能够确定当前行为。代码不能单独确定过去哪一个相反条款已获授权废止。候选一要求先确认行为边界及权威承载位置，符合本轮规划范围。仅在新说明里记录现有代码不能自动解除 `.trellis/spec/backend/index.md:54` 的父 design 优先规则。

唯一最高价值决定是下一任务方向：用户是否需要当前能力的配置说明改进，还是保持现状。可直接询问：

> 下一任务是否选择“保持现有预测与分类的运行行为，统一协变量契约并补齐配置说明”，还是维持现状？

建议选项：

- 配置说明一致化（推荐）：预测继续拒绝两类协变量；分类保留当前过去协变量上下文路径并继续拒绝未来已知协变量；保留角色标注和保存。随后完成限定范围的设计。
- 维持现状：保留 B1 与全部当前产品行为，记录契约差异，结束本轮方向探索。

该问题确认方向，不授予实施、修改冻结归档、运行门槛或提交权限。真正实现协变量输入会改变目标和验证范围，需要重新规划，不能由选择配置说明选项推导。

## 5. 非阻塞成稿建议

### NCR-01：采用 Pydantic 描述修改时，明确纳入两个生成物

- 相关要求：配置/接口说明以源模型为准，生成物保持同步，未来变更范围必须可核查。
- 当前材料位置：`.trellis/tasks/09-30-next-task-planning/research/current-state-candidates.md:97-99` 已建议修改直接 schema 描述，第 128 行仍写“若需刷新生成物”。
- 事实：`src/tsllm/config/dataset.py:28-30` 的 Channel role. 已进入 `web/openapi.json:1792-1802`，并生成 `web/src/api/schema.d.ts:426-432` 的注释。`src/tsllm/service/models.py:39-59` 通过 DatasetConfig/ChannelsIn/ChannelsOut 暴露 ChannelSpec；`.trellis/spec/frontend/api-client.md:9-11` 要求后端模型变更时同步重新生成两个文件。
- 影响：若未来选定修改该 Field 描述，仍把生成物列为未定选项，会遗漏必要范围和一致性证据。枚举和 API 形状无需改变，但生成 JSON 说明与 TypeScript 注释应同步。
- 最小建议：方向确认后将 `web/openapi.json` 和 `web/src/api/schema.d.ts` 明确列入受控生成范围，按实际生成差异限定验收，不能手工修改。若最终仅改 UI、不改模型描述，则可保持两个生成物原样。
- 排除相邻改动：`src/tsllm/config/schema.py:8-14` 导出的是 RunConfig 与 backbone options，`RunConfig.dataset` 为字符串；本轮检索 `web/tests/fixtures/run-config.schema.json` 没有 ChannelSpec 或两个协变量角色。因此单独修改 ChannelSpec 描述不构成改写 RunConfig schema 夹具的依据。

### NCR-02：把预测/分类与合法保存前提拆成可判定的验收子句

- 相关要求：验收必须覆盖已声明的保留语义，并有明确前置条件。
- 当前材料位置：`.trellis/tasks/09-30-next-task-planning/research/current-state-candidates.md:105` 提到四种角色保存、预测拒绝及分类差异，但尚未展开机制。当前是候选阶段，不把该未展开项列为阻断。
- 事实：现有 `tests/service/test_api_basic.py:102-112` 只明确覆盖预测 mixed target/past_covariate 拒绝。对 tests/tasks、tests/runs、tests/service、web/tests 定向搜索两个协变量角色，仅返回这一 past_covariate 用例。`src/tsllm/config/dataset.py:99-106` 要求至少一个非 ignore 通道，`src/tsllm/data/channels.py:31-40` 要求名字集合及配置合法。
- 影响：仅保留现有预测拒绝测试，不能证明分类过去协变量说明准确或两类实验均拒绝未来协变量；“四种角色均可保存”也不能解释为全部通道可改为 ignore。
- 最小建议：成稿时分别覆盖预测过去/未来拒绝、分类过去不被该角色规则拒绝并进入上下文、分类未来拒绝，以及合法混合配置中的四种角色保存。使用合成临时配置、适当控制缓存/能力前提，保持错误优先级和服务无目录副作用。UI 说明在编辑前、编辑中和保存后采用何种可见范围，也应明确；该选择不要求新增能力 API。

### NCR-03：将权威说明和窄范围兼容性写成明确边界

- 相关要求：共享契约优先、冻结原件保护、最小变更和独立验收。
- 当前材料位置：`.trellis/tasks/09-30-next-task-planning/research/current-state-candidates.md:99-101` 正确预留了“被授权的现行契约承载位置”，尚未指定文件和优先关系。
- 事实：`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:3` 与 `.trellis/spec/backend/index.md:54` 要求共享契约一致；本轮禁止改旧任务和冻结材料。
- 影响：只补 UI 提示，或只新增未明确优先关系的说明，均不能证明候选承诺的“契约一致化”完成。反向修改模型校验、角色枚举或静默转换通道则会扩大产品范围。
- 最小建议：方向确认后列出获授权的当前契约文件、与冻结历史材料的关系及直接引用范围。仅说明/描述/生成注释的修改不应触及 validate_job、模型输入、API 形状、队列、缓存哈希或 B1 路由机制；若实际需要改变这些行为，返回规划。

## 6. 验证成本与边界

Python 四门槛与前端三门槛来自真实规范和 package 脚本：`.trellis/spec/backend/quality-guidelines.md:11-25`、`.trellis/spec/frontend/quality-guidelines.md:7-18`。候选一若同时改变 Python 描述与页面，两组门槛均适用。角色保存与说明的 390/1280 px 可见验收有直接相关性，符合 `.trellis/spec/frontend/quality-guidelines.md:45-46`。这些正式命令成本仍需未来环境决定，本轮不把“低至中”解释为已测工时。

最小计划无需默认追加性能矩阵、权重/CUDA或真实训练。若路由和恢复机制保持不变，原恢复单测仍在前端完整门槛内，历史真实恢复证据可明确复用；不能称为本轮重新验证。若未来实际触及路由/加载机制，再执行 `.trellis/spec/frontend/quality-guidelines.md:43-44` 对应真实缺块恢复门槛。

本轮没有执行任何测试、生成、构建、服务、浏览器、性能实验、真实实验、训练、入库、作业提交、下载、安装或 Git 写操作。未读取私有 data/ref/runs/cache 或备份。没有修改研究报告、主会话规划、前轮预审、产品、规范、生成物、旧任务、冻结证据或会话日志。唯一写入为本候选审查报告；未递归派发。

代理审查与研究者共享模型及上下文限制。本次无候选选择阻塞不等于完整方案已通过，也不构成用户选择或实施授权。
