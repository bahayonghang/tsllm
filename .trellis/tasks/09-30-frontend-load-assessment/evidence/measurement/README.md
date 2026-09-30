# 测量工具与复现方法

## 状态与边界

脚本不改变产品源码或正式构建。浏览器观察器通过 Playwright 注入三个方案的同一生产页面。性能浏览器为已安装的 Microsoft Edge，采用 headless、1280×900、DPR 1、本地回环网络，不降速。可见浏览器验收由主会话另行完成。

夹具由 `../fixtures/create_fixtures.py` 直接生成。没有调用入库、提交、训练或模型下载流程。5 个作业写入时均为终态。数据集、指标、预测与曲线均为合成内容。`../fixtures/manifest.json` 记录 34 个文件的 SHA-256、长度和 mtime。

## 准备

下列 PowerShell 变量指向当前任务和主会话记录的隔离目录。`$experiment` 取当前 `task.json` 的 `meta.experiment_root`。Python 使用现有虚拟环境，不调用 uv。Node、Playwright 和 Edge 使用已安装版本，不下载依赖或浏览器。

```powershell
$repo = (Get-Location).Path
$task = Join-Path $repo '.trellis/tasks/09-30-frontend-load-assessment'
$experiment = (Get-Content -Raw -Encoding utf8 (Join-Path $task 'task.json') | ConvertFrom-Json).meta.experiment_root
$python = Join-Path $repo '.venv/Scripts/python.exe'
$runtime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
$node = Join-Path $runtime 'bin/node.exe'
$playwright = Join-Path $runtime 'node_modules/playwright'
$edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
$scripts = Join-Path $task 'evidence/measurement'
$fixtures = Join-Path $experiment 'fixtures'
```

夹具首次创建命令如下。目标非空时脚本停止，保留原文件。后续检查使用 `--verify`。

```powershell
& $python (Join-Path $task 'evidence/fixtures/create_fixtures.py') --root $fixtures --evidence (Join-Path $task 'evidence/fixtures/manifest.json')
& $python (Join-Path $task 'evidence/fixtures/create_fixtures.py') --root $fixtures --verify
```

## 服务

端口固定为 `127.0.0.1:9000`。`--source-root` 为固定提交导出的后端源码，`--variant-root` 为只含 web 的方案副本。runs、cache、configs、web_dist 全部显式传给 `Settings`。`--model-cache` 为独立空目录。启动器设置进程级离线标记和无效代理，保留回环例外；不修改网络、防火墙或 CUDA 设置。

```powershell
& $python (Join-Path $scripts 'serve_variant.py') --source-root (Join-Path $experiment 'source') --variant-root (Join-Path $experiment 'variants/B0') --fixture-root $fixtures --model-cache (Join-Path $experiment 'measurement/models') --check-only
```

`--check-only` 不启动服务。移除该参数后启动对应方案；启动前检测 9000 端口并拒绝占用。仅关闭当前会话自己启动的服务。

## 先做试测

主会话准备并独占 B0 服务后，按以下命令执行试测。试测目录与正式原始记录目录分开。失败记录不覆盖。`--attempt` 默认为 1，返修后的重试递增。

```powershell
& $node (Join-Path $scripts 'measure.mjs') --playwright-root $playwright --browser-executable $edge --fixture-root $fixtures --output (Join-Path $scripts 'pilot') --variant B0 --sample 1
```

## 主矩阵

主会话关闭其试测或可见验收服务并确认 9000 释放后，才运行协调器。协调器每轮轮换方案顺序：B0/B1/B2、B1/B2/B0、B2/B0/B1，然后重复。每个方案每轮执行 6 个场景。5 轮共 90 个有效观测。任何失败都保留原记录并停止本轮；不自动忽略失败，不选择最快样本。协调器核对所服务 HTML 字节，关闭自己拥有的服务进程，校验全部 34 个夹具文件及 mtime。

```powershell
& $python (Join-Path $scripts 'run_matrix.py') --experiment-root $experiment --output (Join-Path $scripts 'raw') --node $node --playwright-root $playwright --browser-executable $edge
& $python (Join-Path $scripts 'summarize.py') --input (Join-Path $scripts 'raw') --output (Join-Path $scripts 'summary.json') --require-complete
```

`--sample-start`、`--sample-end`、`--variants`、`--scenarios` 和 `--attempt` 支持明确的补测。保存补测原因；不得静默覆盖已有观测。

## 完整访问补充场景

`--scenarios journey` 在一个全新上下文中依次访问运行列表、新建表单和真实预览、含 5 个作业的对比、数据集列表、数据集详情、预测详情、分类详情和系统页。重回运行列表也保留资源记录。完整访问累计集合按最后阶段快照的完整 URL 去重。该场景单独标记，不替代主矩阵的 90 个观测。

```powershell
& $python (Join-Path $scripts 'run_matrix.py') --experiment-root $experiment --output (Join-Path $scripts 'journey') --node $node --playwright-root $playwright --browser-executable $edge --sample-start 1 --sample-end 1 --scenarios journey
& $python (Join-Path $scripts 'summarize.py') --input (Join-Path $scripts 'journey') --output (Join-Path $scripts 'journey-summary.json')
```

## 观测定义

- 冷缓存：每个独立观测新建 BrowserContext，并执行 `Network.clearBrowserCache`。保持 HTTP cache 功能启用，首个入口静态资源不得命中缓存。该条件只表示浏览器 HTTP cache，不表示操作系统、进程或代码缓存冷态。
- 缓存复用：在同一页面和上下文中，先完成冷 `/runs`，再重新载入 `/runs`。原始 CDP 记录区分 304、disk-cache、无 disk 标记的缓存事件和网络传输，不能把 reload 自动视为命中。
- 入口：从文档导航起点到页面主体、实际数据和操作控件满足条件后的连续 2 个动画帧。
- 表单：首次进入 `/runs/new` 的主要指标为 form-ready。之后通过真实模板选择填入合成配置，等待 Name、context_length 和 horizon 均已应用，再测量真实“预览并提交”点击到校验后模态框就绪。只关闭预览，不点击最终“提交”。预览时间与资源另列。
- 对比：运行列表禁止勾选入库作业。为覆盖固定混合作业，采用浏览器内部 `history.pushState` 和 `popstate`，标为 programmatic-router-navigation；该指标不标为可信用户点击。其他导航以捕获阶段的可信 click 时间为起点。
- 图表：通过现有 React ECharts 包装器取得已有实例，等待 `finished`、最终尺寸、数值数据、绘制状态与非空彩色 Canvas 像素。预测图还要求 prediction rows 与 context series 请求完成，且上下文、真值和预测均值各有数据。不会用 Canvas 存在、load 事件或固定延时替代就绪。
- 观察器成本：每阶段保存 predicate 累计与最大耗时，以及像素扫描次数/耗时。已完成 Canvas 的像素结果缓存到下一次 rendered 事件。就绪时间包括相同外部观察器成本。长任务不归因于某个包。
- 资源：保存完整 URL、Resource Timing 的 transferSize/encodedBodySize/decodedBodySize，以及 CDP 原始请求、响应头、304/缓存标记和完成字节。Resource Timing 的 transferSize 是浏览器口径，不包含完整 TCP/IP 包开销。
- 导航增量：只统计导航时间窗口中新请求的 URL。累计集合包含目标快照前所有已完成请求，涵盖入口快照后至点击前的资源。共享块按完整 URL 去重；API 的重复请求保留在传输总量中。不同大小响应的 URL 并集使用最大观测 body；完整原始请求均保留。
- 时间：中位数、最小值、最大值及全部样本均保留。FCP 和 Navigation Timing 属于文档载入；SPA 使用独立的浏览器 click-to-ready 时间。
- 汇总中的 `observer_document_max_predicate_ms` 为当前文档累计最大观察器耗时。长任务只统计已在就绪前完成并被观察器记录的任务，按任务区间与测量窗口的交叠毫秒求和；进入点击处理前开始的相交任务也包含在内。
- `journey` 的 `ready_ms` 仅为最后一次系统页导航的耗时，不能解释为完整旅程耗时；该补充场景用于完整访问的累计资源集合。

## 可见复核地址

从 `../fixtures/manifest.json` 读取五个固定 ID。全部 ID 逗号连接到 `/compare?run_ids=` 可覆盖七类警告，共十条消息。预测与分类详情分别为 `/runs/<forecast>` 与 `/runs/<classify>`；合成数据集为 `/datasets/synthetic-alpha`。手工对比选择框保持只列实验作业。所有页面地址包括 `/runs`、`/runs/new`、`/compare`、`/datasets`、`/datasets/synthetic-alpha`、上述两类实验详情和 `/system`。

本目录不得保存截图、依赖、构建包或私有数据。脚本和环境检查通过不等于正式矩阵或可见行为验收通过。
