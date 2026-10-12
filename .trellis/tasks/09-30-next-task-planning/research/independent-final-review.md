---
skill: trellis-plan-review
version: 0.5.0
task_dir: D:/Documents/Code/Python/Exp/tsllm/.trellis/tasks/09-30-next-task-planning
task_name: 09-30-next-task-planning
task_status: planning
review_scope: single-task
task_count: 1
task_members:
  - 09-30-next-task-planning
task_statuses:
  09-30-next-task-planning: planning
verdict: 可执行但需修订
blocking: 0
should_fix: 1
notes: 1
generated_at: 2026-10-01T00:00:00-05:00
---

# Trellis 规划终审报告

## 审阅范围

- 根任务：09-30-next-task-planning
- 模式：single-task
- 任务数量：1
- 有序成员（根优先；顺序不代表依赖）：
  - 09-30-next-task-planning — planning

## 结论

可执行但需修订 — 阻断 0 / 应修 1 / 提示 1

完整方案已经具备进入最终规划展示的条件。三处原先模糊的 path:line 已由主会话补全，并经定向复核：冻结父设计、Settings 源文件、B1 历史验证文件均指向唯一文件。产品门槛、生成、构建、服务和可见验收仍全部标记为未来未运行。

## 问题清单

### TPR-01 · 应修 · V4 Canvas 可见判据仍含主观步骤

- Task: 09-30-next-task-planning
- Affected tasks: 09-30-next-task-planning
- Location: .trellis/tasks/09-30-next-task-planning/design.md:61；.trellis/tasks/09-30-next-task-planning/acceptance-map.md:19-20
- Claim: V4 要求“新鲜合成页面 Canvas 实际可见”，同时要求截图只保留在会话内。
- Evidence: 前端规范要求最终生产构建中的真实页面或 Canvas 验收，见 .trellis/spec/frontend/quality-guidelines.md:43-47。规划没有给出 Canvas 的稳定选择器、页面路径或可计算的可见性阈值。
- Impact: 不同验收者可能对同一页面给出不同结果。jsdom 断言不能替代该门槛，但人工“可见”没有固定的复核输入。
- Route: 保留真实浏览器验收，并补充一个可复核的页面/Canvas 标识和尺寸或可见性谓词，例如在同一视口中记录目标 Canvas 的 bounding box 宽高均大于零，再保留人工文案完整性检查。

### TPR-02 · 提示 · P1 的“其他契约不改”可列出保护边界

- Task: 09-30-next-task-planning
- Affected tasks: 09-30-next-task-planning
- Location: .trellis/tasks/09-30-next-task-planning/acceptance-map.md:7；.trellis/tasks/09-30-next-task-planning/design.md:9,65-71
- Claim: P1 要求冻结父 PRD/design 哈希不变且“其他契约不改”。
- Evidence: M6 已要求保存十文件基线、保护产物/冻结源哈希并在回滚后复核；M7 已列出十文件封闭范围，见 .trellis/tasks/09-30-next-task-planning/design.md:65-86。
- Impact: 现有机制足以约束实施，但“其他契约”没有逐项列名，执行者需要从十文件清单反推允许差异。
- Route: 在最终展示前将 P1 的“其他契约”限定为 M7 以外的共享契约与冻结文件，并绑定 S0/S6 的保护哈希记录。该项不阻止进入规划展示。

## 已关闭问题

- NCR-01 已关闭：M3、S2、M7 明确把 web/openapi.json 与 web/src/api/schema.d.ts 纳入源模型生成链，禁止手改，并要求两次生成幂等。
- NCR-02 已关闭：M4、S4 与 acceptance-map.md:12-17 已拆分 forecast/past、forecast/future、classify/future、classify/past、合法保存、非法保存和哈希前提。
- NCR-03 已关闭：M1、S1 与 M7 明确当前角色支持条款的承载位置、与冻结父设计的关系、优先级和十文件范围。

## 未能核实

- G1-G9、V1-V5、T1-T5、回滚步骤和同修订首败复测均未运行；规划材料明确标记为未来证据，未将源码静态核对当作通过。
- UV_NO_SYNC=1 在当前环境中的工具支持未执行验证；实施前应按 S5 先核实已安装工具和离线参数。
- 分类 past_covariate 的真实运行质量、性能和真实 backbone 行为不在本轮证据中；规划已将其限定为合成能力/缓存前提下的上下文路径检查。

## 可靠部分

- 需求 N1-N7 与验收 P1-P7 均有对应的 M1-M6 机制、S1-S7 步骤和 T/V/G 证据。acceptance-map.md:7-22 逐子句列出角色矩阵、服务副作用、保存哈希、生成幂等、正式门槛、可见验收、首败和回滚。
- 当前运行行为的静态调用链与规划边界一致：known_future_covariate 全任务拒绝，forecast past_covariate 拒绝，classify past_covariate 不触发 forecast 专用拒绝，见 src/tsllm/tasks/validation.py:17-44、src/tsllm/tasks/classify.py:31-47、src/tsllm/data/windows.py:101-137。
- 服务先校验再提交，既有错误映射和无新增运行目录边界有直接依据，见 src/tsllm/service/routes/runs.py:26-35、src/tsllm/service/errors.py:66-67,95-98、tests/service/test_api_basic.py:102-112。
- 生成命令和正式门槛均来自真实源码或规范。G1 的 CLI 定义位于 src/tsllm/cli.py:230-239，G2-G9 的脚本位于 web/package.json:8-12 与 .trellis/spec/backend/quality-guidelines.md:11-25。
- 十文件封闭范围与用户边界一致。M7 只包含两份规范、一个源模型、两个生成物、一个页面和四个测试文件；未把 validation.py、classify.py、路由、RunConfig 夹具、旧任务、冻结证据或产品生成物列为实施修改对象。
- M6 保留首败原件、同修订复测、所有权核对和成对回滚。该机制保护 B1、他人修改、冻结文件和 D3。

## 盲区

An agent reviewing an agent's plan is not an independent second opinion. The reviewer and the author share most of the same blind spots. A clean report means “this pass found nothing”, not “the plan is complete”. Treat the findings as a triage list, not as an approval.
