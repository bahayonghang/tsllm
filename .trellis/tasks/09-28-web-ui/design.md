# 网页设计

接口以 `web/openapi.json` 为准；父任务 `design.md` 第 7 节为接口清单。

## 1. 目录

```text
web/
  package.json
  pnpm-lock.yaml
  biome.json
  tsconfig.json
  vite.config.ts            # /api 代理；vitest 配置（jsdom）
  index.html
  openapi.json              # 由服务导出并入库
  src/
    main.tsx                # QueryClientProvider、ConfigProvider(zhCN)、RouterProvider
    router.tsx
    api/
      schema.d.ts           # openapi-typescript 生成，入库
      client.ts             # openapi-fetch 客户端；ApiError 解析错误信封
      hooks.ts              # 每个接口一个 TanStack Query hook
      sse.ts                # useRunEvents(runId)
    components/
      AppLayout.tsx
      StateTag.tsx
      ErrorAlert.tsx
      charts/
        ForecastChart.tsx
        SeriesChart.tsx
        SegmentTimeline.tsx
        RocPrChart.tsx
        ConfusionMatrix.tsx
        CompareBarChart.tsx
      forms/
        RunConfigForm.tsx
        schemaTransforms.ts # 基座 Options 注入、mode 枚举过滤
    pages/
      DatasetsPage.tsx
      DatasetDetailPage.tsx
      RunNewPage.tsx
      RunsPage.tsx
      RunDetailPage.tsx
      ComparePage.tsx
      SystemPage.tsx
    utils/
      format.ts             # 数字、时间、单位格式化
  tests/                    # *.test.tsx，与 src 结构对应
```

## 2. 路由

| 路径                                      | 页面              |
| ----------------------------------------- | ----------------- |
| `/`                                       | 重定向到 `/runs`  |
| `/datasets`                               | DatasetsPage      |
| `/datasets/:id`                           | DatasetDetailPage |
| `/runs`                                   | RunsPage          |
| `/runs/new?template=<name>&from=<run_id>` | RunNewPage        |
| `/runs/:id`                               | RunDetailPage     |
| `/compare?run_ids=a,b`                    | ComparePage       |
| `/system`                                 | SystemPage        |

## 3. 数据访问

- 所有请求经过 `api/client.ts`；非 2xx 响应解析为 `ApiError { status, code, message, detail }`。
- 查询键：`["datasets"]`、`["dataset", id]`、`["series", id, params]`、`["runs"]`、`["run", id]`、`["metrics", id]`、`["predictions", id, params]`、`["compare", ids]`、`["schema"]`、`["backbones"]`、`["templates"]`。
- 运行列表在存在非终态运行时每 3 s 刷新；运行详情在 SSE 收到 `stage` 或 `end` 事件时使 `["run", id]` 与 `["metrics", id]` 失效。
- 网页状态只存在于 URL 参数与 TanStack Query 缓存；不引入全局状态库。

## 4. SSE

```ts
function useRunEvents(
  runId: string,
  enabled: boolean,
): { events: RunEvent[]; ended: boolean; error: string | null };
```

- 使用 `EventSource`（浏览器在重连时自动发送 `Last-Event-ID`）。
- 为了在组件重新挂载时不重复读取，hook 记住最后事件 id，重新创建连接时使用 `?from=<id>`。
- 收到 `end` 事件后关闭连接。
- 日志区域只保留最后 5,000 条，超过时丢弃最早条目并显示已丢弃数量。

## 5. 表单

- 基础 schema 来自 `/api/schema/run-config`：`run_config`（RunConfig JSON Schema）与 `backbone_options`（基座名 → Options schema），见父设计 3.3。能力、许可与安装状态来自 `/api/backbones`。
- `schemaTransforms.ts`：
  - `withBackboneOptions(schema, optionsSchema)`：把 `backbone.options` 替换为所选基座的 Options schema。
  - `withAllowedModes(schema, capabilities, taskType)`：`mode` 的 `enum` 过滤为允许值；分类任务只允许 `head`。
  - 两个函数为纯函数，单元测试覆盖。
- 表单组件：`@rjsf/antd` 的 `Form`，`validator-ajv8`；`liveValidate` 关闭，提交时校验；服务 422 响应中的字段路径映射到 `extraErrors`。
- `backbone.name` 与 `dataset` 使用下拉，选项来自 `/api/backbones` 与 `/api/datasets`；未安装的基座显示为禁用并提示缺少的依赖。

## 6. 图表

| 组件            | 输入                                        | 说明                                                 |
| --------------- | ------------------------------------------- | ---------------------------------------------------- |
| ForecastChart   | 某起点的上下文序列、真值、均值、q0.1 / q0.9 | 分位带用两条 line + `areaStyle` 叠加；起点处竖线标记 |
| SeriesChart     | series 接口返回的桶均值                     | `dataZoom` 改变范围时按新范围重新请求                |
| SegmentTimeline | 段列表与划分边界                            | `custom` 系列画区间；四个划分用四种颜色              |
| RocPrChart      | `curves.roc`、`curves.pr`                   | 每个划分一条曲线                                     |
| ConfusionMatrix | 2×2 数组                                    | antd Table，不使用 echarts                           |
| CompareBarChart | 对比表中某一指标                            | 按划分分组的柱状图                                   |

- echarts 使用按需导入（`echarts/core` + 所需图表与组件），控制构建体积。
- 颜色从 antd token 读取，保证暗色主题下可读。

## 7. 预测结果取数

- 起点选择器：`/api/runs/{id}/predictions?split=test&limit=500` 返回去重起点列表（父设计第 7 节、service-api R15）。
- 单个起点：`/api/runs/{id}/predictions?split=test&channel=<c>&origin_time=<t>` 返回该起点全部提前量。
- 上下文曲线：series 接口取 `[origin - L*freq, origin]` 范围（L 来自运行配置）。PreparedFrame 已是 `freq` 网格，L ≤ `max_points` 时服务返回原始行。

## 8. 构建与托管

- `vite build` 输出 `web/dist`；服务 `static.py` 托管。
- `web/dist`、`web/node_modules` 加入 `.gitignore`。
- `package.json` 脚本：`dev`、`build`、`check`（`biome check . && tsc --noEmit`）、`format`（`biome format --write .`）、`test`（`vitest run`）、`gen:api`（`openapi-typescript openapi.json -o src/api/schema.d.ts`）。
