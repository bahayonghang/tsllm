# 绘制条目收集修订 paint-collection-r1

日期：2026-09-30（America/Chicago）。修订仅涉及评估脚本和本目录证据。没有修改产品、隔离方案运行时代码、依赖、阈值或原始观测。

## 缺陷与收集顺序

审查证据位于 ../../../review/paint-collection-analysis.json。原 90 条有效记录全部支持 paint API。B0 的 30 个入口快照中 26 个 paint 为空；其中 16 个后续同文档快照包含 startTime 早于入口 end 的原生 FCP。原快照在第二次就绪 rAF 中读取 paint，而原生条目的发布可以晚于该 rAF。

installProbe 的原实现保持不变。该函数仍在原第二次就绪 rAF 冻结 start、end、duration、resources、navigation、longTasks 和探针成本。新增 collectPaint 在同一文档读取原生 Performance Timeline，必要时使用 type: paint、buffered: true 的 PerformanceObserver，等待 FCP 或 1000 ms 超时。awaitReady 返回补充结果后，调用方才可导航、刷新或关闭 context。

- paintAtReady：原就绪快照的完整 paint 数组。
- paint：在补充收集时实际取得的原生条目，按原生 startTime 排序并去重。
- paintCollection.status：observed、timeout、unsupported 或 error。
- paintCollection.startedAt、collectedAt、waitMs：同文档 performance.now 时间轴上的收集时间，独立于页面就绪 duration。
- paintCollection.readyEndpoint：原 end；scope 为 document。FCP 不会被截断到 end，晚于 end 的原生时间也完整保留。

超时或不支持时不推算 FCP。原生 paint 的缺失状态需要在最终报告中明确说明。该修订对 B0/B1/B2 使用同一规则；最终矩阵应使用同一新脚本版本。原矩阵保持历史证据，不回填条目。

## 版本与输出

before/ 保存原 browser_probe.mjs、measure.mjs，snapshot.json 记录脚本哈希及原 raw/ 的 92 个文件哈希：90 个有效观测样本，加 order 和 lifecycle 两个记录文件。原观测中无无效样本，也没有既往失败测量尝试。after/ 保存冻结后的两份脚本，revision.json 记录前后版本、测试和范围检查。

每个新样本的 instrumentation 字段记录脚本 SHA-256、paint-collection-r1 和 1000 ms 收集策略。measure.mjs 在输出目录旁写入 <output-basename>-instrumentation.json。例如 output 为 recovery-r1/raw，则 sidecar 为 recovery-r1/raw-instrumentation.json。已有 sidecar 与当前脚本不一致时停止，防止混合测量版本。已有样本仍按原规则拒绝覆盖。

建议试测输出目录使用 recovery-r1/pilot；完整矩阵使用 recovery-r1/raw。试测和正式样本分开保留。服务、浏览器及 9000 仍由主会话控制，本次脚本修复没有启动这些资源。

## 检查

- node --check：browser_probe.mjs、measure.mjs 和 paint_collection.test.mjs，3/3 通过。
- node --test paint_collection.test.mjs：8/8 通过。覆盖延迟发布、已发布条目、FCP 晚于就绪时间、明确超时、takeRecords 队列、unsupported/error、awaitReady 等待以及原就绪函数不变。
- 使用既有 web/biome.json，对逐字节相同的临时文件执行 Biome lint：3/3 通过，无修复；保留 9、10、2 条 useTemplate 信息提示。
- 初次 stdin 方式的 lint 返回 contents aren't fixed，3 个退出码均为 1。该次没有修改源文件。记录保留在 lint-1*；随后改用实际临时文件执行，结果在 lint-2*。
- 这些文件为独立 JavaScript 评估脚本，没有 TypeScript 类型检查入口。未改变或绕过产品的 check/test/build 门槛。

全部测试使用确定性原生 API 替身与受控时钟，不使用浏览器、服务或网络。实际 paint publication 必须由主会话 cold/warm pilot 和后续同版本矩阵验证。日志仅规范化换行与尾空白，保留首次失败结果。
