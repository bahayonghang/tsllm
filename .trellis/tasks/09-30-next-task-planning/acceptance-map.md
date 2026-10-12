# 需求 → 机制 → 步骤 → 验收证据

2026-09-30。产品验收全部为未来设计，未执行或采集。规划审查通过不表示产品门槛通过。

| 需求/验收 | 设计机制 | 步骤 | 必须取得的证据与判定 |
| --- | --- | --- | --- |
| N1/P1 | M1 D3、现有规范限定条款及三个引用位置 | S1/S6 | C1：逐条比较角色矩阵、用户来源与限定优先级；冻结父 PRD/design 哈希不变；M7 之外的共享契约、冻结文件和产品生成物不在允许差异内。 |
| N2/P2-a | M2 静态通道说明、原选择/保存流程 | S3/S4 | 页面测试：查看/编辑/保存/取消四状态准确可见；四值可选、请求不改枚举；无新增运行提交或角色禁用。 |
| N2/P2-b | M5 最终构建可见验收 | S5 | V1：1280/390 px 完整可读，正确区分预测/分类；不把 target/ignore 标为错误。不以 jsdom 替代。 |
| N3/P3-a | M3 Pydantic→OpenAPI→TS | S2/S4 | G1/G2 输出与 diff；仅预期 role 描述/注释改变，除该 description 后 OpenAPI 深比较相同，enum/default/API 形状与序列化不变。 |
| N3/P3-b | M3 同版本二次生成 | S2 | 两次两个输出逐字节/SHA-256 相同；不将对 HEAD 的预期变化当幂等失败；RunConfig 夹具不动。 |
| N4/P4-a | M4 角色拒绝优先级 | S4 | T1：forecast/past、forecast/future、classify/future 三种合法 JobSpec 拒绝，能力/缓存 sentinel 未调用；异常和当前消息匹配。 |
| N4/P4-b | M4 服务先校验 | S4 | T2：三个组合各 422/NOT_IMPLEMENTED，jobs.submit 未调用、临时运行目录集合不变；不扩大为 CLI/worker 零副作用。 |
| N4/P4-c | M4 有前提的 classify/past、真实过滤与 _embed | S4 | T3：满足 fake 能力/长度/缓存时无 past 拒绝；合成源经真实角色过滤构建 prepared，真实 context_batch/捕获型假 adapter 收到 target+past 原顺序且无 ignore；不训练。 |
| N5/P5-a | M4 合法混合配置保存 | S4/S5 | T4：固定名称集合保留 target，另一通道逐四角色 PUT/GET；名称顺序保持；全 ignore/改名/丢通道失败且 YAML 字节不变。 |
| N5/P5-b | M3 Field 描述不进实例，旧哈希规则 | S2/S4 | T5：说明变更前后相同实例的序列化/哈希一致；单位/说明编辑不改哈希、真实角色变化触发 needs_ingest 的旧断言通过。 |
| N2/N5/P2-c | M5 真实页面与隔离合成 API | S5 | V2：两视口合法编辑保存/GET 一致，另一次取消不发 PUT；如实显示 stale/needs_ingest，不自动入库。 |
| N6/P6-a | M5 完整正式门槛 | S5 | G3–G9 全部退出 0，同修订完整日志；定向用例不代替。当前未运行。 |
| N6/P6-b | M5 真视口/Canvas | S5 | V3：scrollWidth <= clientWidth，文案不截断、控件可用；V4：/datasets/<id> 的“通道曲线”卡片后代 canvas 的 bounding box 宽高均大于零、visibility 非 hidden、display 非 none，且人工确认图表可见；保存后的 stale 表现如实记录。截图只会话内。 |
| N6/P6-c | M5 来源/隔离绑定 | S5/S6 | V5：源树/构建/夹具/Settings/视口身份齐全；只用临时合成数据。历史 B1 恢复注明复用，无新性能或真实数据结论。 |
| N7/P7-a | M6 首败/复测 | S5/S6 | 原始失败输出和真实退出码保存，缺码如实注明；修复差异与同修订相同条件复测关联；不放宽门槛。 |
| N7/P7-b | M6 十文件基线与自有片段回滚 | S0/S6 | ROLLBACK：清单/基线/步骤可复核，B1/他人/冻结证据不在撤销范围；本轮不实际回滚产品。 |

## 本轮规划验收

| 要求 | 权威证据 | 状态 |
| --- | --- | --- |
| R1/AC1 | archive-evidence.md、source-inventory.json、两代理全文补读、既有映射核对 | 已完成；收尾再次核对版本/哈希 |
| R2/AC2 | current-state-candidates.md、independent-candidate-review.md、PRD D3 | 两候选与用户选择已记录 |
| R3/AC4 | dispatch.md、同代理限定返修、未来 independent-final-review.md | 第 1/3 轮，完整终审待完成 |
| R4/AC3 | prd/design/implement 与本映射 | 已编写，待终审 |
| R5 | implement.md G1–G9 与本映射不可替代门槛 | 仅设计，产品门槛未运行 |
| R6/AC5–AC6 | task.py validate、UTF-8/空白、diff --check、完整 status、写入与哈希记录、最终摘要 | 待最终收尾 |
