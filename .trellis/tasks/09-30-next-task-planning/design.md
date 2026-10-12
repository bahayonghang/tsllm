# 设计：通道角色支持边界说明一致化

2026-09-30；planning；用户已选择 C1，保留当前运行行为。本文件设计未来变更，等待完整审查及之后的实施批准。本轮不修改产品或规范。

## M1：契约裁定与负责层

父 PRD 的协变量排除条款（.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:84）与共享 design 的预测 past_covariate 条款（.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:89）冲突。用户 D3 明确选择保留运行行为、统一说明。这是本次目标行为的裁定，不表示历史文字曾经一致。

未来承载位置采用现有规范：在 .trellis/spec/backend/time-series-guidelines.md 的 Overview 后新增英文 Channel Role Support 节。在 .trellis/spec/backend/index.md:17、54 两处共享契约入口及 time-series-guidelines.md:11 的引用处说明限定优先关系：经本方案批准的角色支持条款优先，其他共享契约仍由冻结父 design 定义。新节引用本任务 PRD 的 D3 和本节，不改任何归档原文，不创建新的规范层级。实施验收前不新增 Verified 声明。

| 角色 | 合法配置保存 | forecast | classify |
| --- | --- | --- | --- |
| target | 允许，整体校验仍适用 | 现有预测目标与上下文 | 保持现有上下文及标签机制 |
| past_covariate | 允许标注 | NotImplementedError | 不受 forecast 专用拒绝；满足其他前提时进入现有非 ignore 上下文 |
| known_future_covariate | 允许标注 | NotImplementedError | NotImplementedError |
| ignore | 允许，但不可全为 ignore | 不进入模型所用 prepared.channels | 不进入模型所用 prepared.channels |

共同前提：既有名称集合、顺序、至少一个非 ignore 与其他 DatasetConfig 校验保持；自动发现配置仍遵守当前缓存发现要求。分类仍受 embed 能力、长度、缓存新鲜性、标签等条件约束，不能保证任意配置可运行。纯 ingest 的 run=None 提前返回路径保持。HTTP 拒绝不入队、不建目录只适用于服务先校验路径，不能推广到 CLI --ingest 或 worker 既有目录。

负责层：规范维护者记录支持条款；tsllm.config 提供源描述；tsllm.tasks 保持唯一执行校验；service 保持错误映射；web 解释规则，不实现第二套能力判定。

## M2：中文可见说明

在 DatasetDetailPage 的通道卡片、现有 Table 之前放一处静态说明；查看、编辑、成功保存和取消后均可见。复用页面现有 antd Alert/文本排版，自然换行，保留已有 needs_ingest/stale 提示与表格内部水平滚动。

计划文案：通道角色可在有效配置中保存；保存不代表该配置能运行实验。预测暂不支持“历史协变量”和“已知未来协变量”。分类可将“历史协变量”作为输入上下文，仍须满足模型能力、缓存和其他配置条件；分类暂不支持“已知未来协变量”。“忽略”通道不进入模型输入。

四个 ROLE_OPTIONS、枚举值、Select 和保存/取消行为保持。不禁用角色、不自动转换、不新增提交/入库动作或能力 API，不针对具体数据集、通道或 backbone。错误沿用 ErrorAlert。静态提示不把 target/ignore 描述为错误配置。

## M3：Pydantic 与生成说明

仅修改 src/tsllm/config/dataset.py:28-30 的 ChannelSpec.role Field.description。英文描述对应 M1/M2，不改枚举、默认 target、类型、校验器或实例序列化。按真实生成链更新 web/openapi.json 与 web/src/api/schema.d.ts；禁止手改生成物。

独立候选审查 NCR-01 已确认两个生成物都包含该说明；必须同步。RunConfig.dataset 为 id，web/tests/fixtures/run-config.schema.json 不包含 ChannelSpec，不在范围内。

保存实施前基线。移除预期 ChannelSpec.role.description 差异后，OpenAPI 深比较必须相同；TypeScript 仅对应注释变化。相同工具版本第二次生成后，两文件分别与第一次生成逐字节/SHA-256 相同。生成幂等不要求相对 HEAD 无差异，因为新说明本来应与 HEAD 不同。

## M4：合成兼容性验证

只使用合成夹具和临时目录。保留既有测试/断言/超时，不读取私有根目录，不用真实模型或实验补证。

| 验证 | 机制与判定 |
| --- | --- |
| 三个角色拒绝组合 | 新增 tests/tasks/test_channel_role_contract.py：合法 JobSpec 参数化 forecast/past、forecast/future、classify/future；能力查询和缓存检查使用若到达即失败的 sentinel，证明角色错误优先；异常与现有消息匹配。 |
| 分类 past 路径 | 同文件以 fake embed 能力、合法长度和新鲜缓存前提证明 validate_job 不因 past 拒绝。合成源经真实角色过滤/prepare 路径构造 PreparedFrame，再调用真实 classify._embed；捕获型 fake adapter 检查 target+past 顺序、ignore 缺席，不替换 context_batch，不调用 _fit_head、训练或权重加载。不能手工删去 ignore 来冒充过滤证据。 |
| 服务拒绝 | 扩展 tests/service/test_api_basic.py：上述三个组合分别返回 422/NOT_IMPLEMENTED；jobs.submit spy 若被调用即失败；临时 RunStore 目录集合前后相同。每次隔离，避免其他校验错误掩盖结果。 |
| 保存/哈希 | 扩展 tests/service/test_api_datasets.py：同一名称集合保留 target，另一通道轮换四种角色，PUT/GET 后值和顺序匹配；全 ignore、改名、丢通道仍失败，YAML 字节不变。保留单位/说明更新不改哈希、真实角色变化触发 needs_ingest 的旧断言。 |
| schema | 扩展现有 OpenAPI 用例，断言枚举/default/API 形状不变、描述对应 M1；序列化与哈希基线不因此次 Field 描述改变。完整生成差异由 M3 另证，不能只查某个字符串。 |
| 页面 | 新增 web/tests/pages/DatasetDetailPage.test.tsx，复用 helpers.tsx 的 renderRoute/mockFetch，网络只在 fetch 层替换。覆盖查看→编辑→保存和编辑→取消、四值可选/请求体保持、说明始终可见；保留原页面测试。 |

fake 能力和缓存只隔离前提；不证明任何真实 backbone 的分类质量或性能。合法保存不等于运行许可。

## M5：正式门槛与可见验收

implement.md 中两个生成步骤与 Python 四门槛、前端三门槛分别记录。默认 pytest 排除 gpu/weights；缺已安装依赖则停止，不安装升级。定向用例不能替代完整门槛。

可见验收使用同修订最终生产构建、可见 in-app browser、1280/390 px。隔离副本只含必要版本化源/配置/锁文件与获批差异，使用已安装依赖；禁止整仓复制、私有四根、备份或冻结证据复制。构建仅写隔离副本，原 web/dist 和 .claude/launch.json 保持。

临时 app factory 显式构造 Settings(configs_dir、cache_dir、runs_dir、web_dist)，仅本机环回服务，所有路径位于合成临时目录。src/tsllm/service/settings.py:11-45 没有 TSLLM_WEB_DIST 环境变量映射，不能猜造变量。生成合法合成源、元数据和时间序列缓存以展示真实页面/Canvas；禁止默认工作区根路径、POST ingest/run、真实训练、作业提交或外网。可见动作只用 GET/通道 PUT：查看、编辑四角色、合法保存并 GET 确认、再次编辑后取消。保存后既有 stale/needs_ingest 如实显示，不为演示再次入库。

两视口检查完整文案、控件和 document.documentElement.scrollWidth <= clientWidth。页面路径使用合成数据集的 /datasets/<id>；在“通道曲线”卡片内定位 ECharts canvas（卡片标题文本为稳定锚点，canvas 为后代元素），记录其 getBoundingClientRect().width > 0、height > 0、computedStyle.visibility != hidden、display != none，并保留人工检查图表实际可见。截图只在会话内；持久记录仅合成信息、源码/构建/夹具/Settings 哈希、视口与谓词结果。jsdom 和文字断言不能替代可见验收。

不改 router、AppLayout、RouteLoading；完整前端测试仍运行原恢复用例。旧 B1 真实缺块恢复只作既有机制历史证据，不称本次复验。若实施发现必须触及路由/加载边界，先停止并修订范围，再安排真实缺块恢复。无性能目标/耗时门槛，不做性能矩阵、CUDA或真实数据验收。

## M6：失败、回滚与停止条件

未来每次尝试记录修订/源树/夹具身份、命令、cwd、环境、开始结束时间、原始输出和真实退出码；首败不得覆盖。修复后同修订执行相同门槛，保留关联，不放宽断言/阈值/timeout。环境不具备则标为未运行/受阻。

回滚先核对启动基线和当前所有权，仅撤销十文件中本任务自有片段；新文件确认无他人改动才删除。Field 描述与成对生成物一并恢复，规范例外和 UI 说明一并恢复，避免部分撤销。保留 D3 和失败证据；不 reset/clean、不回退 HEAD、不改 B1/他人文件/冻结材料。回滚后核对完整 status 与保护哈希。回滚动作也需届时授权。

需要修改执行校验、枚举、API 形状、缓存哈希、模型输入或其他共享契约；出现无关生成漂移、同文件冲突、私有数据/新权重/外部操作依赖，或三轮返修仍阻塞时停止。当前方案不授权提交、归档或发布。

## M7：未来封闭变更清单（本轮只规划）

| 文件 | 唯一拟改内容 |
| --- | --- |
| .trellis/spec/backend/time-series-guidelines.md | 限定角色支持节与父契约关系 |
| .trellis/spec/backend/index.md | 两处引用的限定例外 |
| src/tsllm/config/dataset.py | role.description |
| web/openapi.json | 源生成对应说明 |
| web/src/api/schema.d.ts | 源生成对应注释 |
| web/src/pages/DatasetDetailPage.tsx | 静态中文说明 |
| tests/tasks/test_channel_role_contract.py（新增） | 角色矩阵/优先级/上下文合成回归 |
| tests/service/test_api_basic.py | 三组合拒绝与 schema 兼容断言 |
| tests/service/test_api_datasets.py | 合法/非法保存与哈希回归 |
| web/tests/pages/DatasetDetailPage.test.tsx（新增） | 可见文案/编辑/保存/取消组件用例 |

validation.py、classify.py、数据/服务实现、路由和 RunConfig 夹具只读。临时验收材料在未来获批范围内记录，不写旧任务。当前仅写本任务规划、研究、映射和上下文清单。
