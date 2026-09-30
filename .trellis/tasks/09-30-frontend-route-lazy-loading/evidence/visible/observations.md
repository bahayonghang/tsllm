# 可见验收记录

使用最终 B1-r1 正式产物、隔离合成终态夹具和可见 Codex In-app Browser。源与产物 SHA-256 见 `observations.json`，与 `../snapshots/experiment-r1.json` 一致。只访问 `127.0.0.1:9000`。

## 方法与覆盖

- 视口：390 × 844、1280 × 900。29 条 DOM 记录包含完整 URL、页面标题、文档宽度、Canvas 尺寸、空值、复选框和警告码；警告原文在会话 AX/DOM 输出中核对，持久证据提取警告码。
- 七条路由均在两种宽度检查。根地址跳转 `/runs`。数据集列表实际点击详情后，浏览器后退回列表、前进回详情，两种宽度均通过。预测、分类、对比和模板深链接保留 query/hash。
- 运行页有5个终态作业，2个入库作业禁选。实际全选后点击“对比所选（3）”，地址只含3个实验作业 ID。
- 混合对比深链接包含全部5个作业。两种宽度均显示10条警告，覆盖7种警告码；指标空值显示破折号（DOM记录91个空单元格）。柱状图实际显示 val/test 数据和5项图例；窄屏图例分页、宽表在局部滚动区域内。
- 数据集详情实际显示240行、2个运行段、2个通道。目视核对运行段/划分 Canvas 及有缺口的通道曲线 Canvas。两种宽度均有可见曲线。
- 预测详情真实 Canvas 显示上下文、真值、预测均值、区间和预测起点。分类详情真实 ROC/PR Canvas、val/test 混淆矩阵、标签规则与阈值均核对。
- 390 px 实际选择 `synthetic-preview` 模板；1280 px 使用该模板深链接。两者实际点击“预览并提交”进入“提交前预览”，JSON显示 `Synthetic forecast`、`context_length=12`、`horizon=6`，随后点击“返回修改”。未点击最终提交或保存模板。
- 所有29条记录均满足 `scrollWidth == documentWidth`。数据表局部横向滚动和预览弹窗内部滚动保留。

## 真实模块故障与文档重载

故障仅在隔离 B1-r1 产物中临时移开一个模块文件；未修改正式源码、服务逻辑或模块字节。`fault-*-hold.json` 与 `fault-*-restore.json` 保留 SHA-256、大小和 mtime。

| 场景 | 实际操作和结果 |
| --- | --- |
| 1280 px，预测页 | 移开 `RunDetailPage-ZaeUnRMC.js`，带 `?split=test&assessment=recovery-r1#restore` 进入；显示中文失败和“重新加载页面”链接。还原同一文件后实际点击链接，`expectNavigation(..., waitUntil=load)` 成功；pathname/search/hash不变，预测页及真实Canvas恢复。 |
| 390 px，系统页 | 移开 `SystemPage-D01M2jNg.js`，带 `?assessment=empty-fragment` 且空hash进入；显示中文失败。还原同一文件后实际点击恢复链接，文档导航成功；query和空hash保持，系统内容恢复。 |

恢复证据为真实点击和文档导航等待成功，以及恢复后的页面/图表。没有用router重建代替重载，也没有以不存在的timeOrigin读数作证。

## 工具限制与清理

- CUA只读evaluate不提供 `performance`，该首次调用失败保留在会话中；改用文档导航事件验证。性能数据由独立采集工具读取。
- 首次 `viewport.get()` 调用失败；`viewport.reset()` 已成功。随后直接读取页面 `innerWidth/innerHeight` 确认1280 × 720，地址为about:blank，再关闭自有标签。
- 总计17张inline图片，仅在会话显示。未写截图文件。截图用于目视检查，持久证据为结构化DOM记录和文字结论。
- 自有服务session17499通过Ctrl+C停止，终端退出1；停止后socket bind确认9000可用，再交给性能代理。1秒connect_ex返回10035，未将该值解释为连接拒绝。
- 前后夹具、故障资产和清理结果见 `cleanup.json`。
