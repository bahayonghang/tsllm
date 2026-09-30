# 规划调查依据

## 边界

调查日期为 2026-09-29（America/Chicago），基线 7829f557c1aac4d356a2a829b010eaa23de5ebed。上一轮核对 main、本地 origin/main 和远端一致；本轮创建前复核 main、HEAD 和干净工作区。未运行应用测试、构建、服务、入库、训练或下载。

父任务与五个子任务均已归档 completed。AC1 为预装依赖、空模型缓存及进程级离线；整机断网要求已取消。父任务补足可见画布检查及图例修复。依据 .trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:111、:212、:243 及 implement.md:61。本任务不重开历史验收。

## A：英文警告

- src/tsllm/runs/compare.py:46-72 生成六类英文 code/message。
- src/tsllm/service/models.py:117-125 没有运行或划分上下文。
- web/src/pages/ComparePage.tsx:50-57 直接显示 message。
- web/tests/pages/ComparePage.test.tsx:26-28 使用中文夹具。
- web/src/components/ErrorAlert.tsx:5 有按码映射；StateTag.tsx:3 有状态标签。

警告业务判断由下层负责，中文展示归前端。可选上下文支持动态信息及旧响应降级。方案尚未实施。

## B：入库作业

- src/tsllm/config/run.py:112-123 明确 ingest 的 run 为 null。
- src/tsllm/runs/compare.py:17-32 接受两类作业并保留列。
- compare.py:51-65 排除 None 比较值和缺少 split 指标的作业；store.py:133-135 对缺失 metrics.json 返回 None。
- web/src/pages/RunsPage.tsx:83-87 及 ComparePage.tsx:41-46 排除入库选择。
- ComparePage.tsx:9-14 和 web/src/api/hooks.ts:213-222 仍提交 URL 中 ID。
- .trellis/tasks/archive/2026-09/09-28-service-api/design.md:64-69 未规定入库请求返回 422。

静态推导：同数据集且均成功的实验与入库可得到空 warnings、入库指标 null；其他差异仍可能有警告。未做本任务 HTTP 复现。用户已选择保留结果、增加警告，因此新增按 kind 识别的提示，维持 200。

## 质量及服务

- .trellis/spec/backend/quality-guidelines.md:11-18 要求后端四项；:48-56 规定合成离线与轻量导入检查。
- .trellis/spec/frontend/quality-guidelines.md:18 要求三项门槛；:36-43 规定网络 mock 和浏览器宽度。
- .trellis/spec/frontend/api-client.md:9-14 要求同步生成契约类型。
- src/tsllm/service/app.py:22-28 启动作业管理器，验证服务须使用临时合成根目录。
- src/tsllm/service/settings.py:27-37 支持目录环境变量；src/tsllm/cli.py:216-227 支持 serve --port 9000。

## 范围外

构建测量、备份处置和实验结果复盘继续为候选。本任务不建立这些子任务，不读取私有运行内容，不处置缓存。
