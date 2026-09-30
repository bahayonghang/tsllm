# B1 隔离验收工具

日期：2026-09-30（America/Chicago）。这些工具仅操作本任务的隔离副本和证据。产品的 Vite 配置、依赖、锁文件、构建阈值和压缩设置保持原样。所有命令从仓库根目录运行。

## 已准备的版本

- 基线为 `e9ce26a7bd1a4ed67cd30d257354e7345c44dec1`。`isolation/source` 仅含从 Git 导出的后端源码、pyproject.toml 和 uv.lock。
- `isolation/B0` 为基线 web；`isolation/B1-r1` 为最终产品快照。B1 准确改变 5 个允许文件，其余已跟踪 web 文件及原 8 个测试文件保持字节相同。
- `evidence/snapshots/B0-source.json`、`B1-r1-source.json` 保存源码哈希、字节、mtime；对应 `*-build.json` 保存全部正式产物、静态和动态导入图。分析使用已安装 TypeScript 解析器，没有构建插件。
- 权威 gzip 估算使用系统 Python 3.14.7 / zlib 1.3.1.zlib-ng 的 `gzip.compress(compresslevel=9, mtime=0)`，与 recovery-r1 相同。B0 为 776,665 字节，B1 为 796,118 字节，包含 index.html 与全部资产。原 Node gzip 估算保留在 `B0-build-node-gzip-initial.json`，不作为最终估算。夹具、服务及测量调度使用 .venv 的 Python 3.13.11；角色划分见 `evidence/infrastructure/runtime-roles.json`。
- `evidence/snapshots/experiment-r1.json` 绑定两方案源码/产物、夹具和五个测量工具的 SHA-256。每条观测重复保存绑定。修改任一绑定文件后必须建立新修订、新清单和空输出目录。

## 溯源与门槛

`evidence/infrastructure/provenance.json` 保存旧任务来源及原脚本哈希。原目录只读；脚本执行都使用本任务副本。`browser_probe.mjs` 与 recovery-r1/after 字节相同。paint 收集继续采用就绪快照冻结、两次稳定帧及最长 1,000 ms 的原生 FCP 后补收集。资源、navigation、longTasks 和探针成本的原就绪终点保持。

`run_gates.py` 读取 package.json，并核对三个命令完全相同，再通过已安装 `.bin/*.CMD` 执行。没有调用 pnpm 自动安装准备，也没有安装或升级依赖。B0/B1 均完整通过 `check`、`test`、`build`。B1 为 41 条测试。每次命令、输出、退出码和源码版本见 `evidence/gates/`。原 web/dist 未参与构建。

```powershell
$task = Join-Path (Get-Location).Path '.trellis/tasks/09-30-frontend-route-lazy-loading'
$python = Join-Path (Get-Location).Path '.venv/Scripts/python.exe'
$node = (Get-Command node).Source
$playwright = 'C:/Users/lyh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
$experiment = Join-Path $task 'evidence/snapshots/experiment-r1.json'
```

初次导出用 `prepare_isolation.py baseline`；新 B1 冻结用 `prepare_isolation.py freeze-b1 --revision r2`。已有目录或清单不能覆盖。B1 未经协调冻结时不得复制。

```powershell
& $python -B (Join-Path $task 'tools/run_gates.py') --snapshot (Join-Path $task 'evidence/snapshots/B1-r1-source.json')
```

重复执行门槛会保留新 attempt 日志。build 会重新生成该隔离 dist，因此开始可见/性能验收后不重复 build；源码返修必须创建新隔离修订并重新验收。

## 夹具与服务

`isolation/fixtures` 为本轮新生成的合成资料。根目录包含 configs、cache、runs、source、model-cache。5 个作业均为终态，2 个数据集使用 240 行合成数据。manifest 保存 34 个文件的哈希、字节和 mtime。没有执行入库、实验、训练或权重下载。

```powershell
& $python -B (Join-Path $task 'tools/create_fixtures.py') --root (Join-Path $task 'isolation/fixtures') --verify
& $python -B (Join-Path $task 'tools/serve_variant.py') --source-root (Join-Path $task 'isolation/source') --variant-root (Join-Path $task 'isolation/B1-r1') --fixture-root (Join-Path $task 'isolation/fixtures') --model-cache (Join-Path $task 'isolation/fixtures/model-cache') --check-only
```

去掉 `--check-only` 后才启动服务。只绑定 `127.0.0.1:9000`。端口占用即停止。只关闭当前操作创建的服务。全部服务路径显式传入 Settings；进程级离线标志和环回代理继承旧验收口径。`--check-only` 已证明服务创建时未导入 torch。

## 主矩阵与完整流程

主会话先完成可见验收，恢复故障模块的原始字节，关闭自有服务并确认 9000 释放。随后才执行以下命令。两个方案按 B0、B1 顺序交替，5 轮，每方案每轮 6 个场景，总计 60 个主观测。失败或较高值全部保留；脚本遇到失败停止，不选择较快样本。

```powershell
& $python -B (Join-Path $task 'tools/run_matrix.py') --experiment $experiment --output (Join-Path $task 'evidence/measurement/raw-r1') --node $node --playwright-root $playwright --browser-executable $edge
& $python -B (Join-Path $task 'tools/run_matrix.py') --experiment $experiment --output (Join-Path $task 'evidence/measurement/journey-r1') --node $node --playwright-root $playwright --browser-executable $edge --sample-start 1 --sample-end 1 --scenarios journey
```

首个输出目录必须为空。非空且没有 sidecar 的目录、不同版本 sidecar、已有同名记录、已有同名调度计划均拒绝。相同版本的明确补测可使用新的 attempt；所有首次失败保留。每轮核对正式 HTML 字节，记录自有 PID、关闭方式、退出码、端口释放，以及全部夹具哈希/大小/mtime。

`measure.mjs` 在同一浏览器文档内记录资源与就绪。cold 仅表示全新浏览器上下文和清空 HTTP 缓存；不声明 OS、进程或代码缓存冷。warm 是同一文档上下文先完成冷入口后 reload。完整流程包括表单模板及实际预览、混合对比、数据集、预测、分类和系统页，不点击最终提交。

## 描述性汇总与独立复算

```powershell
& $python -B (Join-Path $task 'tools/summarize.py') --experiment $experiment --input (Join-Path $task 'evidence/measurement/raw-r1') --output (Join-Path $task 'evidence/measurement/summary-r1.json') --require-complete
& $python -B (Join-Path $task 'tools/summarize.py') --experiment $experiment --input (Join-Path $task 'evidence/measurement/journey-r1') --output (Join-Path $task 'evidence/measurement/journey-summary-r1.json')
```

实现侧汇总不构成独立检查。独立 checker 以 experiment、原始记录、build 清单为输入，重新计算中位数、完整范围、URL 并集、浏览器传输和静态 gzip。Resource Timing transferSize 与 CDP encodedDataLength 分列；gzip 是离线估算。FCP 属于文档加载；SPA 导航使用既有 click-to-ready 口径。完整流程只有各 1 次，不能据此判断时间稳定性。
