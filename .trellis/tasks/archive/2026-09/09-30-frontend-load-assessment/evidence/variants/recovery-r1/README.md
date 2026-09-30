# 模块恢复修订 recovery-r1

日期：2026-09-30（America/Chicago）。本修订只修改隔离临时 B1/B2 和本任务证据。没有修改主工作区产品、API、锁文件或构建阈值。

## 原因与修复

主会话在实际浏览器隐藏 B1 的 SystemPage 模块，访问 /system?assessment=module-recovery#restore，恢复原模块后点击恢复链接，页面仍显示加载失败。原链接指向相同 pathname、search 和 hash，未明确请求文档重载。B2 的 FeatureLoading 也采用相同链接机制。

RouteLoadError 与 FeatureLoading 保留原恢复链接，点击事件调用 preventDefault() 和 globalThis.location.reload()。浏览器 reload 保留当前地址，并重新建立文档、路由和模块实例。该行为不修改查询参数或 fragment。

修改的临时源码共有 6 个路径：

- B1/web/src/components/RouteLoading.tsx
- B1/web/tests/LazyRouting.test.tsx
- B2/web/src/components/RouteLoading.tsx
- B2/web/src/components/FeatureLoading.tsx
- B2/web/tests/LazyRouting.test.tsx
- B2/web/tests/FeatureLoading.test.tsx

新增断言覆盖有、无 fragment 的两种地址。测试先注入模块失败，再实际点击恢复入口，断言默认导航被取消、reload 调用一次及地址保持。随后重建边界并验证模块成功显示。FeatureLoading 测试结束后恢复原地址。jsdom 的 reload 使用替身；文档真实重载仍需主会话浏览器验证。

## 门槛与失败保留

| 方案 | 修复前完整 test | 修复后 check | 修复后完整 test | 修复后 build |
| --- | --- | --- | --- | --- |
| B1 | attempt 3：2 failed、37 passed | attempt 3：通过 | attempt 4：39 passed | attempt 3：通过 |
| B2 | attempt 3：4 failed、38 passed | attempt 3：通过 | attempt 4：42 passed | attempt 3：通过 |

首轮失败均为 expected true to be false，即恢复点击未取消链接默认导航。所有原业务测试保留。使用现有 run_gates.py 串行执行 package.json 的原始 check、test、build 命令，通过已安装 .bin 包装器避免 pnpm 自动安装准备。没有更改超时、测试阈值、配置或依赖。原始记录位于 ../../variant-gates/。B0 没有运行时代码变化，沿用已记录的原门槛。

## 证据版本与资产

- before/：覆盖前保存的初版补丁、清单、依赖图、工具、说明和相关源文件。snapshot.json 记录初版文件与既有门槛的 SHA-256。
- after/：修订后的全部清单、图和补丁；B0 字节不变。顶层 variants/ 的 B1/B2 文件与 after/ 一致。
- revision.json：每个新增或变更资产的 URL、字节和 SHA-256；移除 URL；21 项受保护配置/契约文件逐字节检查。
- reproduction-check.json：新临时目录应用补丁后，B1 53 个、B2 55 个文件全部与已验收副本一致。

| 方案 | 资产数 | 原始总字节 | 相对初版增量 | gzip 总字节估算 | 估算增量 |
| --- | --- | --- | --- | --- | --- |
| B0 | 2 | 2,420,191 | 0 | 776,665 | 0 |
| B1 | 21 | 2,430,585 | 61 | 796,118 | 43 |
| B2 | 39 | 2,442,905 | 122 | 810,268 | 14 |

这里统计 index.html 与全部输出文件。B1 有 15 个、B2 有 27 个资产 URL 或哈希变化，包括依赖引用变化造成的哈希更新。B1 入口为 index-Bw4YU1Ku.js，SystemPage 为 SystemPage-D01M2jNg.js；B2 入口为 index-iXCYusIl.js，SystemPage 为 SystemPage-GswXUoje.js，功能边界为 FeatureLoading-m16Ul-og.js。gzip 仍使用相同 Python 工具参数，属于静态估算。

## 待复验边界

初版主矩阵、行为及首次失败记录保持不变。B1/B2 的新资产需要完整主矩阵和实际浏览器恢复验证；旧样本不能替代新哈希下的测量。B0 资产哈希完全相同，可复用原样本。主会话负责服务、9000、浏览器、报告和最终验收。该子任务未启动服务、未操作浏览器或端口，也未提交、归档、下载、运行模型或读取私有数据。
