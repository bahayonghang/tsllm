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

- [x] AC1 `pnpm -C web run check`（Biome + `tsc --noEmit`）、`pnpm -C web run test`、`pnpm -C web run build` 全部通过。
- [x] AC2 `pnpm -C web run gen:api` 后 `git diff --exit-code web/src/api/schema.d.ts` 无差异。
- [x] AC3 组件测试：schema 表单在切换基座时切换 Options；不支持的 mode 被禁用；SSE 日志组件按 `Last-Event-ID` 续读；对比页显示警告。
- [x] AC4 在内置浏览器中完成父任务 AC5：配置 → 提交 → 监控日志 → 查看结果 → 对比，不使用命令行。
- [x] AC5 在内置浏览器中完成父任务 AC6 的网页部分：ETTh1 数据集出现在列表中，可入库并提交运行。
- [x] AC6 宽度 1280 px 与 390 px 下页面无横向滚动（表格与图表容器除外）。

## 备注

### 验收证据（2026-09-29，分支 `codex/web-ui`）

| 验收项 | 证据 |
| --- | --- |
| AC1 | `pnpm -C web run check`：Biome 检查 45 个文件无问题，`tsc --noEmit` 0 错误；`pnpm -C web run test`：5 个文件 20 项通过；`pnpm -C web run build`：`dist/assets/index-*.js` 2,418.52 kB（gzip 784.30 kB），仅有 chunk 体积警告 |
| AC2 | `schema.d.ts` 尚未提交，`git diff` 无基准；改为比较文件：`gen:api` 连续两次输出逐字节相同（`cmp`）；`uv run tsllm api openapi --out` 重新导出的文件与 `web/openapi.json` 逐字节相同。提交后可按原命令检查 |
| AC3 | `tests/components/forms/RunConfigForm.test.tsx`：切换基座后 Options 字段切换；mode 下拉只含该基座支持的值；分类任务固定为 `head`；未安装基座被禁用。`tests/api/sse.test.tsx`：重新挂载后以 `?from=3` 续读，id 不大于已收最大 id 的事件被跳过，`end` 后不再连接；超过 5,000 条时保留最新事件并计数丢弃条数；一个刷新间隔内的 `stage` 事件只触发一次失效。`tests/pages/ComparePage.test.tsx`：两条可比性警告均以 `role="alert"` 显示，`null` 显示为 `—` |
| AC4 | 内置浏览器，服务 `uv run tsllm serve --port 8000` 托管 `web/dist`：新建运行页加载模板 `kiln_ridge`，Options 显示 ridge 字段；预览后提交，跳转到运行详情页；运行 `20260929-100609-kiln-ridge-fb35` 约 8 s 后 `succeeded`，页面显示完整日志、划分指标、按提前量与按通道指标表、资源；运行列表勾选 2 个运行后点击"对比所选（2）"，跳转到 `/compare?run_ids=…`，显示 12 行指标、柱状图与 5 条警告。分类运行详情页显示划分指标（含 `n_origins`）、ROC 与 PR 曲线、val 与 test 混淆矩阵、标签规则与判决阈值 |
| AC5 | `/datasets` 列出 ETTh1。ETTh1 缓存原为 fresh，为测试入库按钮，把 `cache/datasets/ETTh1` 改名为 `ETTh1.acc-backup` 后状态显示"未入库"并出现"入库"按钮；点击后跳转到作业 `20260929-101436-ingest-etth1-befd`，约 4 s 后 `succeeded`，日志含 read、resample、segment、split、write、done。随后新建运行页加载模板 `etth1_persistence`，预览并提交，运行 `20260929-101546-etth1-persistence-70a6` `succeeded`，结果页显示预测曲线、按提前量与按通道指标表 |
| AC6 | 11 个页面（系统、数据集列表、2 个数据集详情、运行列表、2 个新建运行模板、3 个运行详情、对比）分别在宽度 390 px 与 1280 px 的同源 iframe 中加载；22 次检查均为 `scrollWidth == clientWidth`，且表格与图表容器以外没有元素超出视口右边界 |

### 图表绘制检查

内置浏览器窗格在验收期间处于隐藏状态（`document.visibilityState == "hidden"`），浏览器不执行 `requestAnimationFrame` 与 `ResizeObserver` 回调。echarts-for-react 在 ECharts 首个 `finished` 事件后才创建实例，所以页面中没有 canvas，截图超时。替代检查：临时 Vitest 文件（检查后已删除）以真实服务数据渲染页面，截获传给 `ReactEChartsCore` 的 option，用 ECharts SVG 服务端渲染器（`ssr: true`）渲染为 SVG。结果：

- 预测曲线：ridge、persistence（ETTh1）各 3 条折线；chronos2 零样本 5 条折线（上下文、真值、分位带下界、分位带宽度、预测均值）。
- ROC 与 PR：各 2 条折线（val、test）。
- 对比柱状图：2 组柱。
- 运行段时间轴：`custom` 系列；通道曲线：折线。
- 全部 option 渲染无异常，SVG 含路径元素。

画布在可见窗口中的目视检查未执行。

### 与规划的偏差

- AC3 原文为"不支持的 mode 被禁用"。实现按设计从 `mode` 枚举中删除不支持的值（`withAllowedModes`），下拉中不出现这些值；测试断言下拉只含支持的值。
- 通道表的"拟合段均值 / 标准差"（R5）：数据集 meta 只有全数据集有效点统计（`eligible_mean`、`eligible_std`），没有 fit 段统计。表头写为"有效点均值 / 有效点标准差"。
- 分类结果的事件阈值：`label_info.json` 中解析后的阈值数值不由接口提供。页面显示配置规则（例如"fit 行分位数 q"）与各划分的判决阈值。
- 新增设计外文件：`utils/guards.ts`、`utils/datasetMeta.ts`、`utils/metrics.ts`、`components/MetricTable.tsx`、`components/RunLog.tsx`、`components/ForecastResults.tsx`、`components/ClassifyResults.tsx`、`components/charts/EChart.tsx`。`schemaTransforms.ts` 另有 `withChoices` 与 `toExtraErrors`。
- rjsf 6.10 在用户修改期间不采用父组件传入的新 schema（`isProcessingUserChange`），`RunConfigForm` 以"基座名 + 任务类型"作为 `key` 重新挂载表单。
- `echarts-for-react/lib/core` 在生产构建中默认导出为模块对象（React 错误 #130），改为 `echarts-for-react/esm/core`。
- `biome.json` 设置 `vcs.root: ".."`，使 Biome 读取仓库根目录的 `.gitignore`。
- 测试夹具 `tests/fixtures/run-config.schema.json` 为服务导出的 RunConfig schema 副本。
- `api/client.ts` 的 `baseUrl` 为 `location.origin`（路径仍为 `/api/...`，不含主机名常量），使 jsdom 与浏览器中 `new Request()` 均有效。
- SSE：已结束运行的日志一次性回放时，逐条渲染与失效导致同一查询约 6 次重复请求。`sse.ts` 改为每 200 ms 最多渲染与失效一次，`end` 事件立即刷新。
- 顶栏菜单：antd 水平菜单的溢出折叠依赖 `ResizeObserver` 测量，在隐藏窗格中未折叠，390 px 下页面宽 477 px。改为 `disabledOverflow` 并允许换行。
- 运行列表中入库作业的复选框禁用，对比页运行选择只列实验运行。原因：入库作业没有指标，对比接口对"实验 + 入库作业"组合不返回警告。
- 分类结果的事件阈值原以 JSON 文本显示，改为中文描述。
- 构建产物为单个约 2.4 MB 的 chunk，`chunkSizeWarningLimit` 设为 2000，未做代码拆分。

### 遗留问题

- 图表画布未在可见窗口中目视检查（见上文"图表绘制检查"）。
- 验收修改了本机缓存：`cache/datasets/ETTh1.acc-backup` 为改名前的 ETTh1 缓存，`cache/datasets/ETTh1` 为网页入库作业新写的缓存。二者均在 `cache/` 中，不入库。是否删除备份由用户决定。
- 对比接口的警告文本为英文（服务端生成），网页按原样显示。
- 对比接口未对"实验运行 + 入库作业"组合返回警告；网页已阻止该组合，服务端行为未改。

