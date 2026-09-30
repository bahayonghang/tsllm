# 前端路由级延迟加载实施与验收

日期：2026-09-30（America/Chicago）。状态：实施和验收完成；尚未暂存、提交或归档。

## 目标

采用旧评估 recovery-r1 的 B1，将现有七个页面按路由延迟导入。保留同步 AppLayout、原路径、根重定向、pathname/search/hash、API 请求和业务行为。提供初始与导航中文加载状态、模块失败提示及真实文档重载恢复。

## 范围与约束

- 产品仅允许 `web/src/router.tsx`、`web/src/components/AppLayout.tsx`、必要路由加载/错误组件和对应 `web/tests`。主会话不写产品，由 trellis-implement 实施。
- 不实施 B2；不改变依赖、锁文件、API/状态/警告码/Schema/生成类型、图表行为、构建阈值、minify、target、压缩、缓存或服务端。原测试与断言全部保留，不提高超时或降低门槛。
- 新任务拥有规划、工具、证据。主会话可更新直接受影响的 frontend specs。旧评估、旧归档、其他任务及范围外文件保持只读。
- 仅用 `127.0.0.1:9000` 和隔离合成 configs/cache/runs/model-cache；不提交作业、不运行实验/训练/入库、不下载权重、不读私有原始数据、不改变网络/防火墙。原 `web/dist`、私有根目录、备份及 `.claude/launch.json` 不写入。端口占用不终止他人进程。
- 不暂存、提交、归档、推送、发布；不强制暂存、不 amend。最多三轮聚焦返修。共享契约或范围冲突、未授权操作及三轮后阻塞须报告并停止受影响工作。

## 验收标准

- [x] AC1 基线与任务：HEAD、完整 status、产品相对 e9ce26a7bd1a4ed67cd30d257354e7345c44dec1 的 diff 可追溯；唯一任务、指定分支、中文规划、真实 JSONL 和 AC 映射；validate 后 start。
- [x] AC2 路由：七条路径按需导入；AppLayout 同步；根重定向、query/hash、导航和原业务/API 保持；非当前页面模块未在 /runs 提前加载。
- [x] AC3 加载恢复：初始/导航中文状态；模块失败中文提示；实际点击执行 document reload 并保持 pathname/search/hash；覆盖空和非空 fragment；真实浏览器恢复同一哈希模块后页面和图表恢复。
- [x] AC4 正式门槛：最终快照完整通过 check/test/build；原测试保留；记录命令、退出码、版本、首次失败；不安装/升级，必要时用与 package.json 一致的已安装 .bin；原 web/dist 不变。
- [x] AC5 可见行为：最终正式产物及合成终态夹具，在 390/1280 px 覆盖七页、深链接、前进/后退、模板和实际预览、数据集/预测/分类真实 Canvas、混合对比、七类警告、空值、入库行禁选；不提交作业；inline 图片最多 20 张，不保存截图。
- [x] AC6 性能采集：同期 B0/B1 交替，六场景各五次，共 60 个有效主观测和两次独立完整流程；复用 recovery-r1 就绪、资源及 paint-collection-r1；新空目录、版本 sidecar、原始快照及失败/高值保留。
- [x] AC7 独立复算：中位数、最小/最大、URL 并集、实际传输、离线 gzip 分列；说明首次使用/完整访问成本及环境限制；旧 54.79%/225.0 ms 不作本次结果或门槛；收益消失先查实现/采集偏差，结论实质改变则停止报告。
- [x] AC8 独立检查：trellis-implement 与独立 trellis-check 真实派发记录、上下文方式及所有权完整；同范围 findings 回灌同一实施代理，最多三轮；最终全范围无未解决问题。
- [x] AC9 清理与保护：夹具 SHA-256/大小/mtime 前后一致；旧材料、范围外跟踪文件、旧 dist/launch 保持；自有服务关闭、9000 释放、故障资产还原、视口恢复、自有标签关闭。
- [x] AC10 交付：验证过的 specs 同步；verification.md 逐项映射 AC、命令、版本、结果、限制、清理；task.py validate、git diff --check、范围检查通过；最终代码与全部验收属于同一修订；明确未提交、未归档。

## 权威来源

本轮用户 Prompt；AGENTS.md；归档父任务 prd/design；旧评估 report/verification、continuation-review、B1.patch、recovery-r1 方案与 instrument 证据。旧临时路径仅为历史信息，不作为执行前提。
