# 网页执行计划

开始条件：`09-28-service-api` 已归档，`web/openapi.json` 存在。

## 步骤

1. 核对 `web/openapi.json` 与父设计第 7 节一致（含 predictions 起点列表模式）；不一致时回到 service-api 修正并重新导出。
2. 初始化 `web/`：`pnpm create vite web --template react-ts`，按设计第 1 节调整目录；安装 PRD R1 所列依赖；TypeScript 固定 `~5.9.3`（openapi-typescript 7.13 的 peer 要求 `^5.x`）。
3. Biome、tsconfig strict、Vitest（jsdom）配置；`.gitignore` 加入 `web/dist`、`web/node_modules`。
4. `api/`：生成 schema.d.ts；client、错误解析、hooks；`sse.ts`。
5. AppLayout 与路由；SystemPage（最小可见页面，用于检查代理与托管）。
6. DatasetsPage、DatasetDetailPage 与 SeriesChart、SegmentTimeline。
7. RunNewPage 与 RunConfigForm、schemaTransforms；单元测试。
8. RunsPage、RunDetailPage（日志、取消、预测与分类结果组件）；组件测试。
9. ComparePage 与 CompareBarChart；警告显示测试。
10. 构建并由服务托管：`pnpm -C web run build` 后 `uv run tsllm serve`，访问 `http://127.0.0.1:8000/`。
11. 内置浏览器手动验收：父任务 AC5、AC6；1280 px 与 390 px 宽度检查。

## 验证命令

```bash
pnpm -C web install
pnpm -C web run gen:api
pnpm -C web run check
pnpm -C web run test
pnpm -C web run build
uv run tsllm serve --port 8000
```

## 审查门禁

- 步骤 7 完成后运行 `trellis-check`，重点检查表单是否只依赖 schema、没有硬编码基座名称或参数。
- 步骤 11 的验收结果以文字记录在本文件末尾。截图含水泥厂数据，不写入仓库。

## 回滚点

- 删除 `web/` 与 `.gitignore` 中的两行即可回滚；服务端 `static.py` 在 `web/dist` 不存在时不挂载，无需改动。

## 步骤 11 验收记录（2026-09-29）

环境：`uv run tsllm serve --port 8000` 托管 `pnpm -C web run build` 的产物；内置浏览器访问 `http://127.0.0.1:8000/`；本机时区 America/Chicago。

1. 系统页显示 GPU、CUDA、库版本与运行目录，无控制台错误。
2. 新建运行（父任务 AC5）：模板 `kiln_ridge` → Options 为 ridge 字段 → 预览 → 提交 → 详情页日志实时显示 → `succeeded`（约 8 s）→ 划分指标、按提前量与按通道指标、资源 → 运行列表勾选 2 个运行 → 对比页（指标表、柱状图、警告）。全过程未使用命令行。
3. 分类结果：`kiln_classify_features` 运行详情页显示划分指标、ROC 与 PR、val 与 test 混淆矩阵、标签规则、判决阈值。
4. 父任务 AC6 网页部分：ETTh1 在数据集列表中；缓存改名后显示"未入库"，点击"入库"跳转到入库作业并 `succeeded`；模板 `etth1_persistence` 提交后 `succeeded`，结果页正常。
5. 宽度检查：11 个页面 × 390 px / 1280 px，全部无横向滚动。修复一项：顶栏菜单在 390 px 下溢出（477 px），改为不折叠并换行。
6. 系统时间按浏览器时区显示（`created_at` 08:43Z 显示为 03:43）；数据时间按原样显示。
7. 图表：窗格隐藏，页面无 canvas；以 ECharts SVG 服务端渲染检查全部图表 option，均正常。可见窗口中的目视检查未执行。
8. 截图未保存，未写入仓库。

验收中修复的问题：SSE 回放时重复请求（合并刷新）；分类事件阈值显示为 JSON（改为中文描述）；顶栏菜单 390 px 溢出；入库作业可被选入对比。

