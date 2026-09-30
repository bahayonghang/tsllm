# 旧评估收尾独立终审

日期：2026-09-30（America/Chicago）。检查角色：独立 trellis-check。检查范围为旧评估任务的全部规划、原始证据、工具、失败、报告和本轮收尾材料。

## 结论

AC1–AC6 通过。没有未解决的范围内问题，可以定向提交旧任务规划和证据。两项本轮检查工具问题已由同一 trellis-implement 代理在第 1 轮修复，首个脚本和失败输出完整保留。没有产品修复。

本结论允许主会话继续本地 Git 收尾。工作提交、独立归档、直接引用更新和会话日志尚由主会话执行；本报告不提前声明这些操作完成。主会话须将最后新增的审计和本报告纳入最终索引字节核对。

## 上下文与范围

- 原生 SubagentStart 注入已发生，包含明确的 Active task。显示结果截断后，读取指定的完整 hook 文件，并分段补读全部受影响规范和任务原文件。旧 report.md、verification.md、continuation-review.md 已完整阅读。
- 读取 AGENTS、trellis-start/check 技能、Phase 2.1/2.2、check.jsonl 全部条目、旧 PRD/design/implement、recovery-r1 方案和 instrument、父平台 PRD/共享设计，以及已归档 B1 的报告、验收和 closure 记录。适用祖先目录未发现额外 AGENTS 或 CONTEXT。
- 历史测量基线为 e9ce26a7bd1a4ed67cd30d257354e7345c44dec1。本轮保护基线为 1b075dc99b5fd4d5174809fe7f3416717c5d0584，保留 codex/frontend-route-lazy-loading 分支上的 B1。旧 task.json 的分支字段保持历史含义。
- 本代理只创建 independent/ 内的新脚本、输出和报告。两份检查脚本的已记录适配由获得明确所有权的 implement 代理完成。本代理未改产品、冻结原证据、Git 索引、依赖、规范或其他任务。未递归派发。

## AC1–AC6 逐条证据

| AC | 本轮核验与证据 | 结论 |
| --- | --- | --- |
| AC1 固定基线、产物、版本、HTTP | 62 项构建文件清单、三份 patch 与 recovery-r1/after 副本一致；图的静态/动态引用均在对应清单内；patch SHA 与 inventory 一致。历史门槛日志 SHA 与 recovery-r1-variant-integrity 一致。Git e9 源码在内存应用补丁后，B1 53 文件、B2 55 文件与历史逐文件记录一致。HTTP 830 条冷入口资产均 200；1,205 条资产响应无 Content-Encoding/Cache-Control。 | 通过 |
| AC2 完整主矩阵 | numerics-main.json 确认 18 组各 5 次、90 个有效主观测，身份不重复，统一 Edge 154.0.4258.37 和 1280×900。轮次顺序与 order 文件一致；每条 attempt=1，最终矩阵没有失败或重试。numerics-journey.json 确认三方案各 1 个完整流程。原修订和全部预检另存，不混入。 | 通过 |
| AC3 资源、时间、完整范围 | 独立执行已审阅的数值核验器，主矩阵 1,349 项、旅程 302 项统计/差值通过，核对 1,755+489 条资产记录。额外核验逐观测、URL 并集、各类别实际 transfer/encoded/decoded、中位数、完整范围与所有差值，共 40,275 个值一致。逐资产离线 gzip 保存值重新求和；未重压缩产物。 | 通过 |
| AC4 完整门槛、双视口、恢复 | 九份最终 gate 日志哈希匹配，check 包含 Biome 和 TypeScript，build 包含 TypeScript 和 Vite；B0/B1/B2 测试为 35/39/42 项，原测试保留。observations.md 和 continuation.md 覆盖 390/1280 px 页面、表单实际预览、Canvas、深链接、七类警告、空值及入库禁选。B1 route、B2 feature 的真实缺块恢复记录与最终清单 SHA 一致；含 query/hash 地址保持。B1 正常页面按仅恢复点击发生变化的范围复用。 | 通过 |
| AC5 报告与决策 | 完整报告的收益、首次使用代价、完整访问成本、波动和局限均有原始记录。B2 2,439.7 ms 高值保留。建议 B1、暂不采用 B2 的判断与数据一致，没有任意新通过阈值。旧 225.0 ms 及百分比属于历史评估；未使用归档 B1 正式实施的 60 条主观测替代或混算。 | 通过 |
| AC6 独立核验、保护、清理、隐私 | 当前 586 个跟踪文件与 3 个受保护文件的哈希、大小均与 preflight 一致。原 463 个任务文件通过固定材料复核，唯一 task.json 新授权保留全部旧字段和原字节副本。38 个忽略日志保存字节相同可跟踪副本。历史 lifecycle、cleanup 和可见记录支持 19 个原服务退出、34 个夹具保持、故障资产还原和视口/标签清理。本轮没有启动服务或浏览器。 | 通过 |

### 数值与版本复核输出

- independent/numerics-main.json、numerics-journey.json、http.json、paint.json 及对应 command JSON：本轮实际重跑，四项退出码均为 0。
- preparation/repair-r1/closure-evidence-v1.json：40,275 个值对照、62 项资产/图绑定、九份正式 gate SHA、历史 Git 对象与当前保护范围。
- preparation/repair-r1/source-replay-v1.json：B1/B2 分别 53/55 个源码逐文件哈希；仅读 Git 对象和任务内材料，在内存重放，没有生成产品源码、构建包或缓存。
- paint.json：93 条记录、108 个文档、213 个就绪快照全部 observed；33 个快照补收 FCP，1 个原生 FCP 晚于就绪终点，额外等待 0–6.8 ms。所有样本和 sidecar 均匹配冻结脚本 SHA；未改变 duration 或资源窗口。
- 正式构建原始长度为 B0/B1/B2 2,420,191 / 2,430,585 / 2,442,905 B；保存的逐文件 gzip 值之和为 776,665 / 796,118 / 810,268 B。gzip 为历史离线估算，实际 HTTP 未压缩。

## 已修复发现

### F1：历史工作树字节与 Git blob 字节口径

文件：independent/closure_verify_v1.py。初版要求历史 289 个工作树 SHA 全部等于 Git blob SHA，导致四项断言失败。

修复由 implement 代理完成。285 项精确匹配；三篇 thinking guide 和 00-bootstrap-guidelines/task.json 使用固定四路径清单，证明其 e9 Git blob 不含 CR，将每个 LF 替换为 CRLF 后严格匹配原工作树 SHA。输出保留两种哈希、长度、转换行数。其他路径不能使用通用换行宽容处理。

失败保留：closure_verify_v1.initial.py.txt、checker-initial-source.json、closure-evidence-command-1.json。失败原版 SHA 为 19e434f600f4b04c124ec86578b0dc44a4c00ceb9b523d9a259d320b0548ba4b。未修改历史基线清单。

### F2：B0 与 B1/B2 重现记录的结构不同

文件：independent/replay_sources_v1.py。初版把 B0 的历史摘要按 B1/B2 的逐文件结构读取，产生 KeyError。

修复由 implement 代理完成。B0 仅核对 source_changes 前后哈希、三份相同 patch 和历史 51 文件、mismatches=[]、原测试保持的摘要，输出 files_checked=null。B1/B2 按实际明细分别验证 53/55 个文件。不声称本轮重放了 B0 的 51 项逐文件明细。

失败保留：replay_sources_v1.initial.py.txt、source-replay-command-1.json。失败原版 SHA 为 b648548ab626979f83454adf5d9ff7fcd4d33a804600a4af256fefcb8b5f675c。原始复现记录保持。

准备工具初版的 Ruff 长行与格式失败也已修复，首次输出及格式前源码保留于 preparation/。以上均为收尾工具问题，没有新增性能测量失败，没有删除旧模块恢复、FCP 采集、pnpm 准备或其他原始失败。

## 材料、敏感性与空白

固定材料共 463 文件、32,877,915 B。审阅用途、UTF-8、JSON/JSONL、后缀、原始空白及凭据候选；没有二进制或凭据模式命中。合成来源由生成器、原始观测标识和测试/可见记录支持。模式扫描仅为辅助证据。

两份大 JSON 为 original-recomputed.json（1,915,287 B）及 recomputed.json（1,915,231 B），分别保留 original 与 recovery-r1 的 90+3 观测派生统计、21 组、完整 URL 和版本。各含 40,792 个标量、4,300 条环回 URL，未包含私有文件内容或构建资产正文。两份文件对保留历史决定和复算均有必要。未读取私有 data/ref/runs/cache 或备份。

material-review-v1.json 保存本代理对 38 份日志原件/副本逐字节、大小、SHA 的比较，全部通过。38 份日志均为 0 B，不能用于证明服务退出。退出依据是原 lifecycle 和 cleanup。prepare --verify 独立重跑确认 463 历史文件、38 副本和 50 条适配引用；不写原件。

task.json 只新增 closure_20260930，旧字段值均保持；原 1,212 B 文件有 SHA 绑定副本。任务局部 .gitattributes 使用 -text 保留原字节，cr-at-eol 识别采集行尾，同时保留三个原空白检查项。根 .gitattributes 在 586 文件保护范围内，保持不变。

本轮没有裁剪任何原文件空白。material-review-v1.json 中工作树和暂存区 git diff --check 均退出 0，stdout/stderr 为空。随后主会话 stage-byte-check-2.json 的 527 个暂存文件均限定旧任务、blob 与工作区原字节一致，完整暂存及工作树空白检查仍为 0。材料审计对末尾空行的描述与 Git 的实际检查结果分别保留；没有预设告警，也没有把历史归档 B1 的空白告警套用到本任务。

## 验证与限制

| 检查 | 结果 |
| --- | --- |
| 新增收尾工具 Ruff check / format --check | 通过；preparation/static-final-* 及 repair-r1/command-* 保留实际输出 |
| 新增收尾工具 Pyright | 通过，0 errors / 0 warnings；F1/F2 修复后对应命令为 0 |
| 数值、HTTP、FCP、报告和来源复核 | 通过；修复后仅重跑受影响检查，未重复已经通过的专用检查 |
| 历史前端完整 check/test/build | 通过；按绑定哈希复用九份记录，没有重建或改变原 web/dist |
| 任务材料及适配引用 | 通过；新版本适配有原件 SHA 和 old→new 映射，B1 冻结清单不变 |
| 当前 B1 与受保护路径 | 586+3 全部保持；本轮产品写入范围为空 |
| 当前索引与空白 | 第二次索引审计 527 文件、0 范围外、0 字节差异；两类空白检查均为 0 |

无未解决的范围内发现。没有共享契约冲突，不需要新的实验、产品范围或依赖变更。无需修改 .trellis/spec/。

历史构建和可见验收按既有证据复用。未读取旧临时目录，未重新构建、重新压缩、重新测量或重开浏览器。B0 的 51 文件记录只有摘要；依赖没有完整事前/事后哈希；这些原有层级和局限已明确保留。

结论仅覆盖历史本机 Edge、环回、合成夹具和既定观察器。390 px 支持布局和交互结论，不支持真实手机性能。完整流程每方案仅 1 次；最后 ready_ms 是系统页导航。没有总体置信区间、真实用户权重、库级 CPU 归因或整机网络隔离结论。

本轮没有新服务、标签、故障资产、网络操作、安装、训练、入库、提交作业或权重下载。本代理未提交、归档、推送或发布。主会话后续记录工作提交、独立归档提交、直接路径修正和会话日志，并再次核对最终索引及 Git 对象。
