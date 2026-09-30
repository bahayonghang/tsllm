# 独立预检

日期：2026-09-30。范围：已批准的 frontend-load-assessment；固定基线 e9ce26a7bd1a4ed67cd30d257354e7345c44dec1。预检时三个方案和测量工具仍在实施。本记录不代表 AC1–AC6 已通过。

## 已识别的问题

### P1：服务启动参数与临时副本结构不一致

- 首次读取时，`evidence/variants/setup_variants.py:49–53` 仅复制根忽略规则和 `web/`。`evidence/measurement/serve_variant.py:23、44` 却要求同一方案目录存在 `src/tsllm/service/app.py` 并从该目录导入服务。原组合无法启动。
- 已在运行矩阵前通知主会话和 measurement 代理。measurement 代理随后报告增加显式 `--source-root`，固定后端来自 `source/`，前端来自 `variants/<name>/web/dist`；B0 `--check-only` 通过。修正脚本及正式服务行为仍待最终复核。
- 本检查代理未修改其他代理所有文件。

### P2：原有 dist 的检查未覆盖新增文件

- `evidence/scope/verify_scope.py:35` 只逐一检查基线记录的文件。若原有 `web/dist/` 新增文件而既有文件未变，该检查仍报告无变化。
- 建议对原有 `web/dist/` 的当前文件相对路径集合与基线集合同时比较，再逐一比对哈希。仅检查该公开构建目录，不读取私有目录。
- 预检未发现实际新增产物；该发现属于最终边界核验脚本的覆盖缺口。修复由主会话协调。

## 已检查的实现边界

- 夹具生成脚本使用合成数据、5 个终态作业、2 个合成数据集、预测及分类指标；直接准备夹具，不执行 worker 或入库流程。脚本断言比较结果覆盖全部 7 个警告码。`evidence/fixtures/create_fixtures.py:160–205`。
- 服务使用显式 Settings 根目录、端口 9000、空模型缓存、进程级离线环境及回环代理例外；不修改防火墙或 CUDA 配置。`evidence/measurement/serve_variant.py`。
- 图依赖采集插件只在构建阶段输出模块和块关系，没有运行时计时探针。`evidence/variants/assessmentGraph.ts:14–48`。`renderedLength` 是模块归属参考，不能直接视为每个依赖的网络节省量。
- 正式 gate 脚本保留每次失败及重跑结果。当前采用已安装 `.bin` 执行 package.json 的原命令，原因是 pnpm 12 自动依赖安装与 junction 冲突；报告必须说明实际启动方式，不能写成已成功执行 pnpm 启动命令。`evidence/variants/run_gates.py:18–48` 与 `evidence/variant-gates/B0-check-1.txt`。
- 初始依赖图插件的 TypeScript 失败已保留，后续需要成功的 check 和 build 证据；不能仅凭 B0 测试通过认定三门槛通过。`evidence/variant-gates/B0-check-2.txt`、`B0-build-2.txt`、`B0-test-2.txt`。

## 矩阵前的测量要求

measurement 代理报告将使用独立浏览器上下文及 CDP 清除 HTTP 缓存，热缓存样本保留首次访问后的上下文；使用浏览器内部的可信 click 起点和组件就绪终点。正式脚本尚未交付时，以下项目保留为待检查：

1. 预测详情须同时等待 prediction rows 和 context series。`web/src/components/ForecastResults.tsx:152–170` 可在 context 返回前先出现图表，首个 Canvas 或非空 future points 不足以证明完整图表就绪。
2. 图表终点包括最终数据、绘制完成和实际非空 Canvas；表单终点包括实际表单和可验证的预览功能。驱动端等待或操作时间不能充当页面就绪时间。
3. 冷缓存定义仅覆盖已执行隔离机制的浏览器 HTTP 缓存。操作系统文件缓存、JavaScript 编译缓存或整个进程冷态须另有证据才可声明。
4. 每次导航使用相同入口状态。入口、导航新增和累计资源按完整 URL 核算；重复请求的实际流量另行保留，不能因 URL 去重而丢失。
5. 主矩阵保留 3 × 6 × 5 个有效样本及全部失败尝试。完整访问累计资源使用同一会话的附加 journey；不能把不同冷缓存样本的字节相加当成一段访问。
6. gzip 估算、HTTP 响应头、Resource Timing 字节、缓存命中、浏览器就绪时间分列。没有 Content-Encoding 时不得用 gzip 估算冒充传输量。
7. 每个方案正式 check/test/build、延迟模块失败及恢复、两种宽度的可见验收完成后，再做最终 AC 对照。

## 预检结论

可以继续完成临时方案和测量工具。正式矩阵前须核实启动接口修正并审查最终 harness。当前没有产品修改、提交或归档授权；本代理只新增本目录的检查材料。

## 脚本就绪后的复核

- 已直接读取修正后的 `serve_variant.py:15、25、46、50`：固定后端使用 `--source-root`，当前方案仅提供 `web_dist`。启动接口问题已修正。
- 审阅 `measure.mjs:53–60` 时发现累计集合遗漏：原式只相加入口快照和目标导航窗口，会漏掉跨过入口终点或在两阶段之间开始的请求。measurement 代理已在任何试测和矩阵开始前修正为目标快照的全部已完成记录。`accounting-regression.mjs` 验证跨窗口资源、缓存重复 URL、导航新增 URL 及流量求和。
- `measure.mjs:144` 单列 `accountingWithPreview`，预览功能对应的额外资源不再遗漏。主计时继续表示表单就绪，真实预览操作单独计时。
- `browser_probe.mjs` 原先逐次扫描 Canvas 的全部像素。measurement 代理已缓存已完成图表的像素结果，并在下次 rendered 事件后失效；阶段记录观察器及像素扫描的调用数、累计和最大耗时。报告仍须说明计时包含共同观察器成本。
- 已独立执行任务上下文校验，implement/check 清单各 12 项通过。`git diff --check` 通过；私有目录跟踪检查空输出。`scope-preflight.json` 记录 289 个跟踪文件未变、暂存区为空、受保护文件哈希及备份存在性符合基线。主会话已补齐 `verify_scope.py:36–38` 的原有 dist 新增及删除文件检查。
- 两份测量 JavaScript 的 `node --check` 通过；独立资源窗口回归 8 个断言通过。已核对当前 B0/B1 check 日志及退出码，lint/type-check 通过；B0 测试 35 项、B1 测试 38 项通过。B2 和最终方案清单仍在实施，不在本预检中判定最终通过。
- 当前未发现阻断试测的静态方法问题。正式 AC 结论等待实际矩阵、完整门槛、可见行为证据和最终独立复算。
