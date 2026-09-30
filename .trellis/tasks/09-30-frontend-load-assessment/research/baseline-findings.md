# 规划阶段只读调查

## 范围

日期：2026-09-30（America/Chicago）。当前分支 codex/compare-warnings，HEAD e9ce26a7bd1a4ed67cd30d257354e7345c44dec1，创建新任务前工作区干净。compare-warnings 已归档，活动指针为空。当前调查只读取代码、规范和已有产物，没有构建、启动服务、浏览器测量或产品修改。

## 确认事实

- web/src/router.tsx:3–9 静态导入 7 个页面；:16 默认进入 /runs，:17–23 定义全部页面路径。web/src 和 service 的搜索未发现现有 React lazy/Suspense 或动态 import 加载边界。
- web/src/pages/RunNewPage.tsx:1–18 引用表单依赖；web/src/components/forms/RunConfigForm.tsx:1–16 使用 @rjsf/antd 与 validator-ajv8。
- web/src/components/charts/EChart.tsx:1–26 已使用 echarts/core、显式图表/组件注册和 CanvasRenderer。不能把当前情况描述为全量 import echarts。
- web/src/pages/RunDetailPage.tsx:15–17 同时静态引用分类和预测结果组件；实际展示按任务类型选择。可作为 B2 调查对象，不预先承诺收益。
- web/vite.config.ts:11–14 使用 dist，警告阈值为 2000 kB。本任务不得提高该值。
- src/tsllm/service/static.py:11–25 通过 FileResponse 提供文件及 SPA fallback；src/tsllm/service/app.py:30–37 没有显式安装压缩中间件。实际 Content-Encoding 和缓存命中仍未测量。
- src/tsllm/service/settings.py:22 接受 web_dist；:27–36 的 from_env 未映射该字段。隔离方案通过现有 Settings 对象传入路径，不修改产品接口。
- web/tests/helpers.tsx 使用 routes 创建内存路由，并在 fetch 层提供合成响应。临时延迟加载方案须保持该测试边界。

## 已有产物

文件：web/dist/assets/index-DlIxrfbQ.js。这里只读该本地产物，不将其认定为本次固定提交重建证据。

| 观测 | 值 | 口径 |
| --- | --- | --- |
| 文件长度 | 2,419,860 字节 | 当前文件实际长度 |
| SHA-256 | 9d4690a2705c2b1e2a906c9933ff9c88ee4fc37ca9cd048f7d6e1fd77fb9853f | 当前文件实际字节 |
| gzip 长度 | 776,403 字节 | Python gzip.compress，compresslevel=9、mtime=0 |
| 既有 Vite gzip 报告 | 785.11 kB | compare-warnings 原构建日志；参数口径与本轮 Python 计算不同，不能直接混算 |

这些值不证明实际传输压缩已开启，也不证明任何页面加载慢。需要对同一固定基线进行 HTTP 与浏览器测量。

## 尚待执行验证

- 打包器最终保留的模块、共享块与入口加载集合。
- 当前静态服务的 Content-Encoding、缓存验证和浏览器传输字节。
- 浏览器冷缓存机制、性能 API 和功能就绪计时能力。
- B1/B2 对入口、首次功能使用、累计资源和失败处理的真实影响。
- 各临时方案的正式前端门槛及可见行为检查。

## 边界

不读取私有目录内容或处置备份。不复制数据值、研究报告或论文文本。规划阶段没有运行 uv、训练、入库、权重下载、Git 提交、推送、归档或新分支操作。
