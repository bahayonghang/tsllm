# Research: 产品现状与下一任务候选

- Query: 保留当前 B1，在现有产品和归档证据中识别最小、可独立验收的下一任务。
- Scope: internal。限定父平台、前端评估/B1 收尾、协变量配置至任务入口调用链，以及已完成对比警告任务的排除核对。
- Date: 2026-09-30（America/Chicago）。
- 状态：只读研究完成；本文保留候选阶段结论。2026-09-30 主会话已收到用户选择：说明一致化，保留运行行为，规划契约说明、UI/schema 提示及必要生成文件同步（D3）。共享契约的裁定、权威承载位置及完整设计由主会话继续负责；没有实施授权。

## Findings

### 1. 结论与建议

提出两个选项。推荐将“协变量能力边界与配置提示一致化”作为最小下一任务的候选，前提是用户确认继续保持当前预测拒绝协变量的语义。该候选不包含协变量模型能力。若用户当前没有配置指导需求，则维持现状，保留已验收 B1，也有充分依据。研究不把推荐当作用户已选择。

确认的问题是文档之间存在可定位的契约差异，以及通道角色界面缺少适用范围说明。现有拒绝逻辑符合父 PRD 和 runner 子设计，并有服务测试覆盖。因此，本报告不把差异直接认定为预测实现缺陷，也不建议删除校验来启用协变量。

本轮没有证据支持追加 B2、压缩、缓存或服务端优化。没有新增性能测量、真实用户访问比例或新的性能故障报告。既有包大小、构建 warning 和历史耗时不能独立支持这些方向。

### 2. 上下文加载与阅读边界

- 收到完整 `<!-- trellis-hook-injected -->` 和 `Active task: .trellis/tasks/09-30-next-task-planning`，没有 `Full hook output saved to` 提示。采用注入路径，未运行 `task.py current`、create 或 start。
- 已读取根 `AGENTS.md`、本任务 `research.jsonl` 三个真实条目及其源文件、当前 `prd.md`、trellis-brainstorm 与 research 技能、workflow 的规划和 2.1/2.2。读取时本任务尚无 `design.md` 或 `implement.md`。未加载 implement/check 清单；映射 JSON 中出现清单名只用于识别归档适配。
- 当前目录及 `src/`、`web/`、`tests/`、`.trellis/` 中未发现适用的嵌套 AGENTS.md 或 CONTEXT.md；根 CONTEXT.md 不存在。没有创建缺失上下文。
- 首次批量读取发生工具输出截断，随后按行补齐所需原文。下列八份必读文件均已完整阅读；37508 字节的旧报告分为 1–195 和 196–394 行读取。部分并行范围的截断内容也已单独补读。
- 当前 HEAD `945a76ecf35303083aec36acd5e879a3aa409aba`、分支 `codex/frontend-route-lazy-loading` 及当前产品树与 B1 工作提交一致，来自主会话本轮核对；本研究角色没有运行 Git 命令。出处：`.trellis/tasks/09-30-next-task-planning/research/archive-evidence.md:7-8`。

| 已全文阅读的材料 | 行数 | 用途 |
| --- | ---: | --- |
| `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md` | 295 | 已确认决定、产品需求、范围、验收和遗留事项 |
| `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md` | 374 | 共享契约、分层、数据与适配器形状、运行/API |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md` | 394 | 历史 B0/B1/B2 评估和结论边界 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/verification.md` | 62 | 历史 recovery-r1 验收、失败和恢复 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md` | 53 | 旧评估后续已完成的提交、归档和适配 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/independent/final-review.md` | 87 | 旧证据独立复核与保留的限制 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md` | 109 | B1 正式实施的独立版本与结果 |
| `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md` | 96 | B1 AC1–AC10、门槛、可见验收和真实恢复 |

B1 `evidence/closure/README.md`、`result.md` 全文已读，archive-receipt 与 postarchive-validation 已读；precommit、log-preservation、receipt-launcher-failure、stage-byte-check-1、stage-whitespace-check-1 已解析。未重跑任何历史核验器。旧引用使用 `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/preparation/reference-adapters/mapping.closure-v1.json` 的已有映射定位；未更改冻结报告、清单或原脚本。四份适配件哈希和 50 个目标存在性的完整验证由主会话完成，见 `.trellis/tasks/09-30-next-task-planning/research/archive-evidence.md:36-43`；本报告不声称重复做过该验证。

### 3. 已完成能力与应排除的重复任务

| 事实 | 证据与推断边界 |
| --- | --- |
| 数据契约、六适配器、预测/分类、文件运行记录、服务和网页均已实现。父 AC1–AC7 已完成。 | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:22-107`、`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:111-131`、`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:260-266`。这是历史验收，未读取私有运行来重做验收。 |
| 整机断网并非未完成验收项。 | `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:111-117`、`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:243-258`。用户取消整机条件，批准进程级离线。不可重新包装成必须补做的下一任务。 |
| 七条路由已延迟导入，同步 AppLayout 保留；显式恢复保留 pathname/search/hash 并 reload。 | 当前源码 `web/src/router.tsx:1-63`、`web/src/components/RouteLoading.tsx:5-38`。历史可见与真实恢复验收见 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md:11-20`、`.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md:69-78`。没有本轮新浏览器验证。 |
| B1 工作提交与归档已完成。 | `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/result.md:5-12`。工作提交 934ba580，归档 40648784；旧 report/verification 中“未提交”是采集时点说明。 |
| 旧加载评估后续收尾也已完成。 | `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md:9-19`、`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md:43-53`。不得再次推荐“归档旧评估”。 |
| 对比警告中文化与混合入库作业警告已有独立任务完成。 | `.trellis/tasks/archive/2026-09/09-29-compare-warnings/prd.md:77`、`.trellis/tasks/archive/2026-09/09-29-compare-warnings/prd.md:95`；当前 `web/src/components/CompareWarnings.tsx:5-13`、`web/src/components/CompareWarnings.tsx:24-58`、`web/src/pages/ComparePage.tsx:51`。父 PRD:295 的旧遗留不能直接变成新任务。 |

### 4. 性能证据分层

- 旧评估：recovery-r1 为 90 个主观测、3 个补充流程；旧 B1 冷入口中位数 225.0 ms。结论支持当时 B1，不支持当时 B2。出处：`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:7-13`、`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:298-322`。
- B1 正式实施：同期 60 个主观测、2 个完整流程；历史冷入口中位数 300.2→234.0 ms，首次功能访问增加 20.1–33.6 ms，暖入口范围重叠。出处：`.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md:7-34`。两批数据不可混算。
- 两批均限定历史版本、合成夹具、本机 Edge 和环回网络。没有用户访问频率，不能计算加权用户收益。出处：`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:312`、`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:379-383`；`.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md:91-99`。
- 包体积 warning 只说明产物体积；离线 gzip 估算不是实际 HTTP 传输；FCP 可由加载状态触发。出处：`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:75-91`、`.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/report.md:302`；`.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/report.md:36-59`。本轮不以任何旧数值宣称当前性能缺陷或新验收通过。

### 5. 协变量：历史决定、当前行为与调用影响

#### 5.1 可确认的历史文本

1. 用户已确认 D3：默认全部目标，不使用未来已知协变量；没有单独明确 past_covariate 的执行语义。出处：`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:14-20`。
2. 父 PRD 明确“过去协变量与未来已知协变量输入”均不在本轮范围，角色可标注，运行时报未实现。出处：`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:80-85`。
3. 父共享 design 写预测使用 target 与 past_covariate，只拒绝 known_future_covariate。出处：`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:89`。子设计不得修改共享契约，见同文件 `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:3`；backend 规范声明父 design 优先，见 `.trellis/spec/backend/index.md:52-56`。
4. runner 子设计又明确预测存在 past_covariate 时抛 NotImplementedError，并要求在 schema 描述注明。出处：`.trellis/tasks/archive/2026-09/09-28-experiment-runner/design.md:53-60`。runner PRD 只列 known_future_covariate，见 `.trellis/tasks/archive/2026-09/09-28-experiment-runner/prd.md:17`。
5. backend 错误规范把预测 past_covariate 作为允许配置但未实现的示例。出处：`.trellis/spec/backend/error-handling.md:37`、`.trellis/spec/backend/error-handling.md:121`。

在所读父/子规划、相关规范及针对性 workspace 文本搜索中，未找到专门裁定上述冲突的用户决定。不能把一个条款视为已经获得用户授权的自动修订方向。

#### 5.2 当前调用链

| 层 | 当前事实 | 完整定位 |
| --- | --- | --- |
| config | 四种角色均可序列化；数据集仍要求通道名唯一、至少一个非 ignore 通道，并排除保留列与时间列；role 描述只有 Channel role.，没有适用范围 | `src/tsllm/config/dataset.py:26-32`、`src/tsllm/config/dataset.py:98-107` |
| 数据集 UI | 四种角色均可选；编辑/保存处没有协变量任务适用说明；已有提示只说明重新入库 | `web/src/pages/DatasetDetailPage.tsx:28-34`、`web/src/pages/DatasetDetailPage.tsx:73-83`、`web/src/pages/DatasetDetailPage.tsx:121-163` |
| 数据集保存 API | 保存要求名称集合与原配置一致且无重复，并通过 DatasetConfig 校验；返回新配置哈希及 needs_ingest，不执行实验能力验证 | `src/tsllm/data/channels.py:21-42`；`src/tsllm/service/routes/datasets.py:75-84` |
| 运行预览 UI | RunConfig schema 校验后显示预览；最终提交异常由 ErrorAlert 显示 | `web/src/pages/RunNewPage.tsx:75-102`、`web/src/pages/RunNewPage.tsx:158-189`；`web/src/components/ErrorAlert.tsx:17`、`web/src/components/ErrorAlert.tsx:31-40` |
| 服务提交 | validate_job 在 jobs.submit 前执行，角色失败发生在入队之前 | `src/tsllm/service/routes/runs.py:26-35` |
| 任务校验 | 所有实验拒绝 known_future_covariate；仅 forecast 拒绝 past_covariate；角色检查早于缓存 fresh 检查 | `src/tsllm/tasks/validation.py:17-44` |
| HTTP 错误 | NotImplementedError 映射 422、NOT_IMPLEMENTED，保留错误消息 | `src/tsllm/service/errors.py:66-67`、`src/tsllm/service/errors.py:95-98` |
| CLI | 常规运行在 _execute 前校验；显式 --ingest 可先执行入库，不能宣称所有 CLI 路径零副作用 | `src/tsllm/cli.py:140-156` |
| worker | 对已有目录在读取 prepared 和加载模型前再次校验；main 的 running/env 记录先于该校验 | `src/tsllm/runs/worker.py:39-51`、`src/tsllm/runs/worker.py:54-74` |
| 回归测试 | mixed target/past_covariate 的 POST 返回 422 NOT_IMPLEMENTED；所有拒绝提交没有新增运行目录 | `tests/service/test_api_basic.py:102-112` |

#### 5.3 为什么不能直接解除拒绝

数据读取保留所有非 ignore 通道（`src/tsllm/data/source.py:17-20`）。context_batch、targets 与 segment_set 使用同一个 prepared.channels（`src/tsllm/data/windows.py:101-137`）；预测的指标与输出也使用该列表（`src/tsllm/tasks/forecast.py:50-55`、`src/tsllm/tasks/forecast.py:94-120`）。共享 ContextBatch/ForecastOutput 没有独立协变量字段或目标通道映射（`.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:180-227`）。因此，仅删除拒绝会把过去协变量一并作为预测目标和评价通道；该判断是基于调用链的静态推断，本轮未执行配置实验。

分类不受 forecast 专用的 past_covariate 拒绝规则；其余能力、缓存及配置合法性条件仍须满足（`src/tsllm/tasks/validation.py:22-44`）。通过这些前提后，分类表示提取使用 context_batch 的全部 prepared.channels（`src/tsllm/tasks/classify.py:31-47`）。提示不能笼统声称 past_covariate 在所有任务均未实现，也不能声称该角色保证分类运行成功。本轮未对该组合做新增运行验收；主会话将按用户已选择的保留运行行为方向明确契约说明。

### 6. 候选一：协变量能力边界与配置提示一致化（有条件推荐）

| 项目 | 内容 |
| --- | --- |
| 问题 | 父 PRD、共享 design 和子设计的 past_covariate 表述冲突；角色编辑与 schema 没有适用说明。当前拒绝在最终提交时出现。证据见第 5 节完整定位。 |
| 用户价值 | 配置前获知角色用途和限制；避免为不能提交的预测配置投入编辑、预览或手动入库步骤。未观测实际浪费频率或时长，不量化收益。 |
| 当前行为 | 两类协变量可在满足既有名称与至少一非 ignore 等约束的合法混合配置中标注保存；预测拒绝两类协变量；所有实验拒绝 known_future_covariate；分类 past_covariate 不受 forecast 专用拒绝，其他能力、缓存和合法性条件仍适用。 |
| 建议行为 | 按用户已选择的保留运行行为方向，由主会话设计契约裁定及通道配置的中文适用提示/schema 描述。保留角色值、合法保存能力，以及角色拒绝的服务提交返回 422 且不新增运行目录；不自动改角色、不静默降级、不新增模型输入能力。 |
| 负责层 | 共享契约维护者负责规则裁定；tsllm.config/任务层负责定义和校验；web 的 DatasetDetailPage 负责解释规则。服务沿用已有错误映射。 |
| 最小范围 | 一个可独立验收的“配置说明与实际校验一致”交付。限定角色说明、直接 schema 描述、所需合成测试、对应规范/契约说明。若修改 ChannelSpec Field 描述，必须从源同步生成 web/openapi.json 与 web/src/api/schema.d.ts；不能手改，也不因此纳入 RunConfig schema fixture。主会话先在设计中确定被授权的现行契约承载位置、与冻结父设计的优先关系及直接引用范围；本研究不裁定文件位置或优先关系，冻结归档不得直接重写。 |
| 非目标 | 协变量输入实现、适配器能力扩展、新 API/能力注册系统、动态前置校验接口、训练/评价算法、数据再入库、通用错误国际化、B2/压缩/缓存/性能优化。 |
| 兼容风险 | 不得把分类 past_covariate 错标为全面不支持或无条件可运行；不得移除合法角色枚举、放宽保存约束或阻止合法混合配置保存；不得改变 validate_job、模型输入、API 形状、HTTP 状态/错误码、队列、缓存哈希或 B1 路由机制；不得用补写说明掩盖父共享契约冲突。需要改变上述行为时返回规划。 |
| 验证成本 | 低至中：源码/契约一致性核对，受影响 Python 四门槛与前端三门槛，合成角色组合和 390/1280 px 可见说明验收。无权重、GPU、真实实验或性能矩阵需求。只规划，未执行。 |
| 推荐理由 | 证据可直接定位，交付边界小；保留当前已验收功能和 B1；验收结果不依赖私有数据或未知使用频率。相较真正实现协变量，不需要立即重设批次和评价契约。 |

可观察验收建议只用于未来规划，尚未执行。角色保存限定在名称集合保持、名称唯一、至少一个非 ignore 通道且满足既有 DatasetConfig 约束的合法混合配置；四种角色仍可显示与保存，不承诺全 ignore 配置可保存。默认目标配置和原页面测试保持；协变量提示准确区分预测与分类，target/ignore 不产生误导性提示。编辑前、编辑中和保存后的提示可见范围由主会话设计明确。

| 未来合成组合 | 前提与可观察结果 |
| --- | --- |
| forecast + target/past_covariate | 合法名称与配置；服务提交保持 422 NOT_IMPLEMENTED，拒绝前后运行目录集合相同。角色校验仍先于能力/缓存检查，不改变错误优先级。 |
| forecast + target/known_future_covariate | 合法名称与配置；服务提交保持 422 NOT_IMPLEMENTED，拒绝前后运行目录集合相同。 |
| classify + target/past_covariate | 设置合法且支持 embed 的能力前提与新鲜合成缓存；该角色不触发 forecast 专用拒绝；直接核对分类 context_batch 包含对应非 ignore 通道。不把上下文断言当作完整分类运行成功，也不对允许路径套用“无新运行目录”断言。 |
| classify + target/known_future_covariate | 合法名称与配置；服务提交保持 422 NOT_IMPLEMENTED，拒绝前后运行目录集合相同。 |

四个组合分别覆盖角色拒绝与分类上下文边界；现有 `tests/service/test_api_basic.py:102-112` 仅明确覆盖第一个组合，不能替代其余三个组合的未来证据。所有新增检查使用合成临时配置，不执行真实实验。

用户方向已经由主会话收到，未授权实施。契约裁定、权威承载文件及其与冻结父设计的关系仍由主会话的完整设计解决；本报告不把现有实现自动提升为高于共享 design 的规则，也不修改规范或产品。

### 7. 候选二：维持现状，保留 B1

| 项目 | 内容 |
| --- | --- |
| 问题与用户价值 | 当前没有新增运行故障或性能要求证据。暂停新增产品任务可以避免没有用户目标的能力扩展，并保持已有验收结果。 |
| 证据 | B1 已完成见 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/evidence/closure/result.md:5-12`；旧评估收尾建议保留 B1 见 `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/completion/closure-result.md:53`；当前路由/恢复见 `web/src/router.tsx:1-63`、`web/src/components/RouteLoading.tsx:5-38`。 |
| 当前/建议行为 | 保留所有产品、配置和 B1 行为；研究记录协变量差异及其未决状态，等待具体研究需求或用户配置问题后再选任务。 |
| 负责层与最小范围 | 本次规划层，仅保存研究与方向决定，不涉及产品层交付。 |
| 非目标 | 不创建替代性性能任务，不将已完成警告/归档/离线验收重新立项，不暗中修订协变量契约。 |
| 兼容风险 | 产品行为无新增变更风险；现有协变量说明差异继续存在。以后涉及该能力时必须先裁定。 |
| 验证成本 | 仅研究材料、引用、所有权和范围检查。产品门槛、浏览器、恢复、性能全部不重跑；历史通过不改写成当前运行结果。 |
| 推荐理由 | 若用户没有配置说明需求，该选项优于没有证据的新功能或优化。该选项可直接结束当前方向探索。 |

### 8. 未来验证来源与证据边界（全部未运行）

| 类型 | 未来门槛与来源 | 适用范围 |
| --- | --- | --- |
| Python 正式门槛 | `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest`；`.trellis/spec/backend/quality-guidelines.md:11-25`；`pyproject.toml:44-65` | 修改 Python/schema 时全部执行；默认排除 gpu/weights。只用合成临时目录。 |
| 前端正式门槛 | `pnpm -C web run check`、`pnpm -C web run test`、`pnpm -C web run build`；`web/package.json:6-12`；`.trellis/spec/frontend/quality-guidelines.md:7-18` | 修改页面时全部执行；不得修改参数、超时、阈值或依赖来通过。历史已安装 .bin 执行方式见 `.trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md:39-49`，未来执行前仍核实环境。 |
| schema/API 一致性 | 修改 ChannelSpec Field 描述时，必须先 `uv run tsllm api openapi --out web/openapi.json`，再 `pnpm -C web run gen:api`，同步两个生成物且不得手改。来源：`.trellis/spec/frontend/api-client.md:9-11`；描述现已进入 `web/openapi.json:1792-1802` 与 `web/src/api/schema.d.ts:426-432`。 | 未来受控范围明确包含 web/openapi.json 与 web/src/api/schema.d.ts 的对应说明/注释差异，枚举和 API 形状保持。本轮未生成。RunConfig.dataset 只有 id 字符串，run_config_schema 导出 RunConfig 与 backbone options（`src/tsllm/config/run.py:93-103`、`src/tsllm/config/schema.py:8-14`）；单独修改 ChannelSpec 描述不纳入 web/tests/fixtures/run-config.schema.json。 |
| 合成离线 | 分别覆盖第 6 节四个预测/分类角色组合、合法混合配置保存及提示边界。`tests/service/test_api_basic.py:102-112`；`src/tsllm/data/channels.py:31-40`；`src/tsllm/config/dataset.py:99-106`；`.trellis/spec/backend/quality-guidelines.md:46-56` | 对拒绝的服务提交断言无新目录；对分类过去协变量在能力/缓存条件满足后核对上下文，不能将两类证据混用。只用合成临时配置，不能读取私有四根或使用真实作业替代。 |
| 可见验收 | 同一修订正式构建、390/1280 px、中文说明可见且不溢出，角色可保存，默认页面/深链接可用。`.trellis/spec/frontend/quality-guidelines.md:38-47` | jsdom 不能替代真实可见验收。截图保持会话内；仅使用隔离合成数据。 |
| 真实恢复 | 保留原有路由恢复单测。若未来修改 route/loading 边界，须用同修订隔离产物执行真实缺块、恢复同哈希文件、实际点击、query/hash 与页面/Canvas 恢复。`.trellis/spec/frontend/quality-guidelines.md:43-45` | 候选一不计划修改路由机制，可明确复用 B1 同机制历史恢复证据；不得把复用写成新增复验。若受影响则启用真实门槛，mock reload 不替代。 |
| 性能 | 本候选没有性能目标，不设置百分比或耗时门槛。若方向变为性能，需新授权的同修订对照和完整样本。`.trellis/spec/frontend/quality-guidelines.md:22-24` | 旧 225/234 ms、包大小及 warning 不充当新门槛。 |
| 失败与回滚 | 首次失败保留原输出和修订身份，修复后同条件复测；仅回退未来任务自有说明/提示/测试改动，保留 B1、他人改动及冻结材料 | 若触及共享契约或发现语义被改变，停止实施并回到规划。不得用删除失败、放宽断言或修改旧报告恢复通过。 |

### 9. 相关规范、代码模式与外部参考

- 当前配置、校验和错误码链是复用点：`src/tsllm/config/dataset.py:26-32` → `src/tsllm/tasks/validation.py:17-44` → `src/tsllm/service/errors.py:66-67`。不要在页面复制完整运行能力判定。
- 页面已有通道标签和 Alert 模式可复用：`web/src/pages/DatasetDetailPage.tsx:28-34`、`web/src/pages/DatasetDetailPage.tsx:73-83`；角色说明必须是中文，枚举值保持。
- schema 与类型来源规则：`.trellis/spec/frontend/index.md:40-45`；表单说明优先回到 Pydantic，见 `.trellis/spec/frontend/forms-and-charts.md:21`。
- 共享契约层级：`.trellis/spec/backend/index.md:17`、`.trellis/spec/backend/index.md:54`；错误处理：`.trellis/spec/backend/error-handling.md:37`、`.trellis/spec/backend/error-handling.md:121`；跨层导读：`.trellis/spec/guides/index.md:31-40`。
- 外部参考：本轮没有外部 API 或库兼容性问题需要外部检索。Python 声明来自 `pyproject.toml:9-26`，前端声明来自 `web/package.json:14-42`；这些是当前文件约束，不宣称本轮已安装版本。归档报告中的 Edge/工具版本只适用于各自历史验收。

## Caveats / Not Found

- 事实：文档差异、校验顺序、UI 文案和已存在测试可从当前文件确认。假设：提前说明能减少配置返工；未观测实际发生频率。用户决定：支持边界是否保持、是否值得作为下一任务。
- 在限定材料内未找到用户明确裁定 past_covariate 冲突的记录。D3 仅说明默认目标和未来已知协变量，不能填补该决定。
- 没有运行产品测试、构建、服务、浏览器、性能实验、真实实验、训练、入库、作业提交、下载、安装升级或网络设置操作。没有读取私有 data/ref/runs/cache 或备份。没有 Git 操作。
- 只写本任务 `research/current-state-candidates.md`；未写规范、配置、依赖、生成物、旧任务、冻结材料、会话日志或他人研究文件。未递归派发。
- 候选阶段的方向问题已由用户答复：说明一致化，保留运行行为，规划契约说明、UI/schema 提示及必要生成文件同步。主会话负责记录 D3 并完成设计；本报告不再次提出方向问题。真正实现协变量不在该决定范围内，未获实施授权。
