# React 配置与结果展示网页

父任务：`.trellis/tasks/09-28-tsfm-platform/`。接口契约见父任务 `design.md` 第 6、7 节，以及服务导出的 `web/openapi.json`。

## 目标

提供数据集查看、运行配置、运行监控、结果展示与运行对比的网页。全部操作通过服务 REST 与 SSE 完成，网页不直接读取文件。

## 依赖

- `09-28-service-api` 已归档，`web/openapi.json` 已生成并入库。

## 需求

- R1 技术栈（2026-09-28 npm registry 核对的版本）：Vite 8、React 19、TypeScript 5.9（strict）、pnpm、antd 6 + @ant-design/icons 6、@rjsf/core + @rjsf/antd + @rjsf/validator-ajv8 6.x、echarts 6 + echarts-for-react 3、@tanstack/react-query 5、react-router 8、openapi-typescript 7 + openapi-fetch、Biome 2、Vitest 5 + @testing-library/react + jsdom。
- R2 API 类型由 `web/openapi.json` 生成（`pnpm gen:api`），手写代码不重复声明接口类型。
- R3 界面语言为中文。数据时间（序列、起点、段、划分边界）为不带时区的 ISO 字符串，按原样显示，不做时区换算。系统时间（`created_at`、`finished_at`、事件 `ts`）为带偏移的 UTC ISO 字符串，按浏览器本地时区显示。
- R4 数据集列表页：id、数据源、频率、通道数、入库状态（fresh / stale / missing）；未入库或过期时提供"入库"按钮（提交入库作业并跳转到作业监控页）。
- R5 数据集详情页：
  - 通道表（名称、角色、单位、描述、拟合段均值 / 标准差 / 缺失比例）。
  - 运行段时间轴与划分边界（fit / val / cal / test）。
  - 通道曲线：选择通道与时间范围，调用 series 接口按需加载。
  - 通道角色编辑：保存后若 `needs_ingest` 为真，显示提示与"重新入库"按钮。
- R6 新建运行页：
  - 表单由 `/api/schema/run-config` 渲染；选择基座后，`backbone.options` 表单切换为该基座的 Options schema。
  - `mode` 下拉只启用该基座 `capabilities.forecast_modes` 中的值；分类任务固定为 `head`。
  - 可从 `/api/run-templates` 加载模板、另存为模板。
  - 提交前显示 JSON 预览；提交成功跳转到运行详情页；422 错误在对应字段显示。
- R7 运行列表页：状态、名称、类型、数据集、基座、模式、创建与结束时间、主要指标；按状态、类型、数据集过滤；勾选多个运行后进入对比页。
- R8 运行详情页：
  - 状态标签与阶段进度；排队或运行中可取消（二次确认）。
  - 实时日志：SSE 订阅，断线后按 `Last-Event-ID` 续读，终态后停止。
  - 配置与环境快照（折叠面板）。
  - 预测结果：选择划分、通道、起点，显示上下文、真值、预测均值与 10–90% 分位带；按提前量与按通道的指标表。
  - 分类结果：各划分指标表、ROC 与 PR 曲线、混淆矩阵、标签规则与阈值。
- R9 对比页：多运行指标对齐表、所选指标柱状图、服务返回的可比性警告（醒目显示）。
- R10 系统页：GPU、CUDA、各库版本、运行目录路径。
- R11 开发时 Vite 代理 `/api` 到 `http://127.0.0.1:8000`；生产构建输出 `web/dist`，由服务托管。

## 验收标准

- [ ] AC1 `pnpm -C web run check`（Biome + `tsc --noEmit`）、`pnpm -C web run test`、`pnpm -C web run build` 全部通过。
- [ ] AC2 `pnpm -C web run gen:api` 后 `git diff --exit-code web/src/api/schema.d.ts` 无差异。
- [ ] AC3 组件测试：schema 表单在切换基座时切换 Options；不支持的 mode 被禁用；SSE 日志组件按 `Last-Event-ID` 续读；对比页显示警告。
- [ ] AC4 在内置浏览器中完成父任务 AC5：配置 → 提交 → 监控日志 → 查看结果 → 对比，不使用命令行。
- [ ] AC5 在内置浏览器中完成父任务 AC6 的网页部分：ETTh1 数据集出现在列表中，可入库并提交运行。
- [ ] AC6 宽度 1280 px 与 390 px 下页面无横向滚动（表格与图表容器除外）。
