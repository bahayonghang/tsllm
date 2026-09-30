# 路由延迟加载验收

日期：2026-09-30（America/Chicago）。基线：e9ce26a7bd1a4ed67cd30d257354e7345c44dec1。分支：codex/frontend-route-lazy-loading。

## 当前状态

AC1–AC10全部通过。产品、正式门槛、可见验收、60+2性能观测、独立数值/范围及最终报告检查均完成，独立checker未发现未解决的范围内问题。最终文档哈希由evidence/review/final.md固定。没有暂存、提交、归档、推送或发布；旧评估任务保持原状。

| AC | 当前状态 | 证据/待完成项 |
| --- | --- | --- |
| 1 | 通过 | evidence/scope/preflight.json、git-status-before.txt、product-baseline.diff；规划与13条 JSONL，正式 start |
| 2 | 通过 | router七条lazy、同步AppLayout；LazyRouting/RouteResolution真实组件与URL断言；review/product-review.md；measurement/runs-route-modules-r1.json证明入口只有当前Page模块 |
| 3 | 通过 | 受控导入初始/导航加载、失败、实际点击reload与空/非空hash测试；visible/recovery.json两次真实缺块与恢复；fault-*-restore.json同hash/size/mtime；预测Canvas恢复 |
| 4 | 通过，保留首次日志工具限制 | gates/B0-*-1及B1-r1-*-1均退出0；B1 41 tests，原8文件/27 tests保持；implementation/gates保留首次失败与最终成功，具体退出码限制见下文 |
| 5 | 通过 | visible/observations.json的29条记录和observations.md；390/1280 px七路由、深链接/历史、真实Canvas、模板实际预览、七警告类、空值、禁选；17张inline图片，无截图文件、无提交 |
| 6 | 通过 | measurement/raw-r1、journey-r1：交替60主观测及2完整流程，全部有效/attempt1，两个采集命令退出0，无测量重试；sidecar、顺序和原始高值保留 |
| 7 | 通过 | review/numeric-review.json：10,303项检查、0失败；62条身份一致；中位数/范围、完整URL并集、transfer、逐文件gzip、HTTP/FCP复算；report.md列实际收益和首次/完整访问成本 |
| 8 | 通过 | dispatch/dispatch.md记录两个trellis-implement及独立trellis-check；product、gates、numeric、visible和scope检查已通过；无产品finding、0轮产品返修；最终报告见review/final.md |
| 9 | 通过 | scope/final.json及review/scope-final.json：旧评估463文件、旧dist2文件、launch和范围外跟踪文件保持；34夹具不变；故障资产还原、9000释放、视口恢复/标签关闭；measurement/cleanup-r1.json |
| 10 | 通过 | 仅directory-structure.md和quality-guidelines.md更新；同修订绑定完成；最终validate/diff均通过，独立终审核对数值、AC、清理与同修订，最终文档哈希见review/final.md |

## 最终修订与运行时

全部B1正式门槛、可见验收及性能观测使用同一冻结源码与正式产物，没有在采集之间重新构建。两个故障模块仅临时移开，恢复后字节和mtime一致。

| 项目 | 值/证据 |
| --- | --- |
| B0源码版本 | d7ed55a3ad1ff91a8c94e9e122e2f73af5c28cfdb4e739a0a11b9547dad98c16 |
| B0产物版本 | 8d7bc493b3c3dbcefbd4ef3987b82ee4eacac7bdcb4f5684f5e7e5d40065fa43 |
| B1源码版本 | 9da4838b462bfc8cd5181ebd5c7cc0bffe43122c72ac8cd9b5c933b95201f07a |
| B1产物版本 | a27404802c27827e1f4c2955517400f8fd4e56b77cd8862f93d6c0fad8b937a7 |
| 权威绑定 | evidence/snapshots/experiment-r1.json；SHA-256 b301cf4c79742aa2c4ff5f89519db087388e538329f0ca06ef20c08c9941044e |
| 前端工具 | Node26.7.0、Biome2.5.14、TypeScript5.9.3、Vitest5.0.2、Vite8.3.1；React19.3.0、react-router8.4.0 |
| 采集浏览器 | 已安装Edge154.0.4258.37、Playwright1.62.1，headless，无CPU/网络节流 |
| Python用途 | 夹具/服务/采集调度：.venv Python3.13.11；权威gzip：Python3.14.7、zlib1.3.1.zlib-ng，level9/mtime0；用途不能混写 |

版本来源为infrastructure/final-preparation.json、runtime-roles证据、build清单和原始browser字段。未安装或升级任何依赖。

## 正式命令与退出码

核实web/package.json后，在isolation/B0和isolation/B1-r1内使用已安装node_modules/.bin/*.CMD执行完全相同子命令，避开pnpm自动安装准备。run_gates.py记录cwd、launcher哈希、参数、源码版本、开始时间、完整输出及退出码。原web/dist未参与构建。

| 对应package命令 | 实际完整脚本 | B0 | B1-r1 |
| --- | --- | ---: | ---: |
| pnpm -C web run check | biome check . && tsc --noEmit | 0 | 0 |
| pnpm -C web run test | vitest run | 0，27 tests | 0，41 tests |
| pnpm -C web run build | tsc --noEmit && vite build | 0 | 0 |

记录：evidence/gates/B0-{check,test,build}-1.json/.txt和B1-r1-{check,test,build}-1.json/.txt。独立校验见review/product-gates.json。原测试、断言、timeout、依赖、锁文件、生成类型、Vite阈值/minify/target均保持。

性能命令从仓库根执行：

```powershell
.venv/Scripts/python.exe -B .trellis/tasks/09-30-frontend-route-lazy-loading/tools/run_matrix.py --experiment .trellis/tasks/09-30-frontend-route-lazy-loading/evidence/snapshots/experiment-r1.json --output .trellis/tasks/09-30-frontend-route-lazy-loading/evidence/measurement/raw-r1 --node D:/GreenSoftware/node/node.exe --playwright-root C:/Users/lyh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright --browser-executable "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
```

两方案各一次完整流程使用相同参数，output换为journey-r1，并加 `--sample-start 1 --sample-end 1 --scenarios journey`。两命令均退出0。描述性summarize使用 `--experiment`；主矩阵加 `--require-complete`。原始工具调用和服务生命周期记录保留在measurement目录。

## 观测口径与结果

冷入口就绪300.2→234.0 ms；暖入口97.1→97.5 ms；首次表单183.6→203.7、对比1128.7→1158.3、数据集详情1134.5→1168.1、预测详情1131.2→1159.9 ms。以上均为n=5中位数，全部范围、资源与成本见report.md。没有使用历史225.0 ms作为本次结果或门槛。

冷入口资产正文2,419,860→1,094,078 B。完整流程transferSize 2,488,723→2,505,056 B，API transferSize两者均67,301 B。全部构建文件离线gzip 776,665→796,118 B。gzip、Resource Timing transferSize、CDP encodedDataLength分别报告。

性能收益定位：暖入口中位数没有改善，但样本范围高度重叠。warm-readiness-analysis-r1.json核对版本、缓存与计时口径；未发现实现/采集偏差，精确原因未查明。冷入口减量和就绪收益保留，首次使用成本已披露，B1的入口优化结论未实质改变。

FCP使用修复后的paint-collection-r1，冻结原ready窗口后补收原生文档条目；142快照/72文档全部observed，33需补采，2次FCP晚于ready，补采0–4.9 ms。未把SPA旧FCP当作导航FCP，未改原ready耗时。

## 首次失败与限制

- implementation/gates/check-1退出1：新增测试格式。test-1日志保留8 failed/33 passed；GBK日志输出错误使首次测试子退出码未写入，外层launcher退出1。相同源码test-2记录退出1和同样失败。未伪造首次子退出码。
- 新测试对当前Router规范化后的Component/element假设错误，修正为真实组件身份核对。check-2的测试辅助类型循环退出2。最终check-3/test-4及隔离三门槛均通过。原测试/断言/超时未改。
- 两个首次日志launcher失败、构建分析工具首次失败、工具格式/检查失败均保留在implementation/gates或infrastructure；没有覆盖失败后只保留成功。
- 描述性summarize首轮局部identity变量覆盖导致Mixed instrument误报。保留summary-attempt-1和修复前源码，仅更名局部变量并重新汇总。62条采集的版本绑定独立复算一致，没有真实混版或重采。
- 原计划记录timeOrigin/navigation.type的可见恢复证据未取得：CUA只读evaluate不提供performance。实际使用真实链接点击、expectNavigation(waitUntil=load)成功、同一完整URL和恢复后的页面/Canvas证明文档导航；单测reload替身不作为真实重载证据。
- viewport.get()不可用；reset已执行，随后页面innerWidth/innerHeight确认1280×720、about:blank，再关闭标签。17张inline图片，无截图文件。
- report生成首次传输引号错误发生在shell执行前，未写文件；evidence/report-launcher-failure.json记录修正，不影响产品或观测。
- 本机环回、合成终态数据、5次主样本和各1次完整流程限制外推；未测试私有实际数据、真实训练、整机离线、其他浏览器或部署网络。

## 清理与范围

visible/cleanup.json：34夹具hash/size/mtime保持；2个故障文件恢复同hash/size/mtime，held文件为空。主会话可见服务Ctrl+C退出1，随后bind确认9000可用。1秒connect_ex的10035保留，未误写为连接拒绝。

measurement/cleanup-r1.json：10次主矩阵加2次完整流程的自有服务均通过自有进程组CTRL_BREAK关闭，服务退出码均为3；对应测量/调度命令均退出0，未把主动中断退出写成正常退出0。前后夹具一致，model-cache为空，9000已释放。独立scope-final再次确认连接拒绝；主会话scope/final.json也确认可绑定。

scope/final.json：HEAD不变、指定分支、暂存区为空；旧评估463文件、原dist2文件、launch的hash/size/mtime保持。仅2个已跟踪产品文件、3个新增产品文件和2篇直接frontend specs改变；所有新增证据/工具位于本任务。未读取私有根文件。

## 最终主会话命令

evidence/scope/final-commands.json记录task.py validate、git diff --check、git diff --cached --check，均退出0。validate保留旧report注入超限warning；三个代理均已补读完整文件。最终命令日志工具第一次在执行前因stdin换行转义失败退出1，未执行门槛或写结果；改为chr(10)后成功，首次失败保留于final-command-launcher-failure.json。

## 已知工具事项

- 当前线程原有同一 Goal 已启用；重复 create_goal 被拒绝，随后 get_goal 确认同一目标处于 active。没有创建第二个 Goal。
- 旧 report.md 为37508字节，超出原生单文件注入32768字节；两个实施代理均补读完整报告。validate 提示为 warning，退出码0。
- 新可见浏览器标签初始为about:blank。首次 viewport 文档调用使用未绑定 browser 标识而失败，随后显式绑定已选浏览器2并读取接口；未执行应用操作或截图。
