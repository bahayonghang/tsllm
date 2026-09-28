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
