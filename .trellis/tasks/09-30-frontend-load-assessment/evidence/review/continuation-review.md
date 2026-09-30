# 独立续检记录（完成）

日期：2026-09-30（America/Chicago）。固定基线为 `e9ce26a7bd1a4ed67cd30d257354e7345c44dec1`。最终测量修订为 `recovery-r1`，测量工具修订为 `paint-collection-r1`。本检查仅写 `evidence/review/`，未修改产品、临时方案、原始样本、汇总、报告或可见浏览器记录。

## 结论

AC1–AC6 通过，无未解决的验收阻塞。最终报告逐项说明三个方案的收益、代价、波动和限制，数值与独立复算一致。B1 可作为后续产品拆分候选，当前 B2 不建议采用；产品实施、提交和归档仍需后续授权。

最终报告仅使用 recovery-r1 的 90 个主观测与 3 个补充旅程。原始测量、原报告、首次失败和返修前产物均保留，不与最终修订混算。终审后 report.md 仅将 AC5/AC6 状态改为通过，最终 SHA-256 为 `a23ad2bfc48bf5ef233d279295accaaf46c6772f7bc2124f4440412276494f9a`。verification.md 与 implement.md 的最终状态另经最小文档复核。

## 验收追踪

| 条件 | 结论 | 独立检查与证据 |
| --- | --- | --- |
| AC1 基线、产物、版本及 HTTP | 通过 | `recovery-r1-variant-integrity.json` 核对 62 个资产、源补丁、锁/API 文件、构建配置和依赖图；`recovery-r1-http-review.json` 核对压缩与缓存。依赖包没有完整事前/事后哈希快照，报告已保留该限制。 |
| AC2 三方案主矩阵 | 通过 | `recovery-r1-numeric-review.json`：18 组各 5 个有效观测，共 90 个；无无效样本。测量失败与重试均为 0，三方案按轮次交替。 |
| AC3 资源、时间及复算 | 通过 | 主矩阵 1,349 项统计/差值、1,755 条资产记录；补充旅程 302 项统计/差值、489 条资产记录，全部匹配。报告额外复算的 93 个观测、21 组和 2,277 项核对与当前修订一致。 |
| AC4 正式门槛及可见行为 | 通过 | 三方案 check/test/build 通过，原测试保留；双视口正常行为和真实路由/功能恢复有对应记录。B1 正常页面按恢复补丁的有限影响复用，B2 正常行为使用修复后产物。 |
| AC5 报告与建议 | 通过 | report.md 的数值、资源口径、样本范围、推荐、局限、复现命令和失败记录均与证据一致，没有预设收益阈值或宣称未测指标通过。 |
| AC6 独立检查、范围及清理 | 通过 | `recovery-r1-scope.json`、`recovery-r1-cleanup-review.json` 与最终材料审计通过；289 个跟踪文件不变，服务关闭，合成夹具保持，浏览器清理有主会话记录。 |

## 发现与修复

1. **真实恢复点击缺陷，方案归属代理已修复。** 原 B1 含 query/hash 的同 URL 恢复链接未重载文档；首次失败保留于 `../visible/module-failure.json`。隔离 B1/B2 的 RouteLoadError 与 B2 FeatureLoading 现取消链接默认动作，再执行 `globalThis.location.reload()`。回归测试实际点击控制，覆盖有、无 fragment 的地址，确认重载一次及 URL 保持。修复前失败与修复后通过均保留；`module-recovery-r1-route.json` 和 `module-recovery-r1-feature.json` 记录真实浏览器恢复成功。检查代理没有修改方案。
2. **原生绘制条目收集过早，测量归属代理已修复。** `paint-collection-analysis.json` 确认全部原始样本声明支持 paint；B0 26/30 个入口快照没有 paint，其中 16 个后续同文档快照包含发生在入口终点之前的 FCP。修订在继续导航前补采原生 Timeline/buffered observer，保留原 `start/end/duration/resources/navigation/longTasks` 和 `paintAtReady`，额外等待不计入就绪时长。8 项确定性检查通过，完整矩阵按同一冻结工具重新运行。
3. **检查工具后缀清单遗漏，检查代理已修复。** 材料审计允许已要求保留的 `.log` 服务日志及 `.tsx` 返修前源码快照。首次失败保留于 `continuation-artifact-audit-initial.json`。未改写被审计证据。
4. **检查命令与 Windows socket 状态，检查代理已修复。** 首次内联清理命令的换行传输导致 SyntaxError，保存为脚本后修复。带超时 socket 返回 Windows 10035，未能代表最终连接拒绝；改用普通阻塞环回连接检查后，9000 返回 10061。`recovery-r1-cleanup-command-failure.json` 和 `recovery-r1-cleanup-review-initial.json` 保留首次失败。这些失败发生在检查工具，不属于性能矩阵失败。

以上变更没有修改产品公共接口、模块归属或任务范围。产品和规范保持不变，无需同步 `.trellis/spec/`。

## 数值与版本核对

B0/B1/B2 正式构建总量为 2,420,191 / 2,430,585 / 2,442,905 B；逐文件 gzip 估算为 776,665 / 796,118 / 810,268 B。当前 62 个资产与清单匹配，B1/B2 源码重现分别为 53/55 个文件逐字节一致。原 8 个测试文件未改。

冷 `/runs` 资产 body 为 2,419,860 / 1,094,078 / 1,096,528 B，对应 1/9/18 个资产 URL；就绪中位数为 303.8 / 225.0 / 227.6 ms。首次表单中位数为 184.1 / 197.1 / 419.5 ms。完整旅程实际总 transfer 为 2,488,399 / 2,503,783 / 2,522,952 B。报告对这些收益与成本的解读与样本范围一致。

B2 首次预测详情的 2,439.7 ms 样本有效，保留于中位数和最小–最大值统计，未删除或补采；原因未查明。每方案 1 次补充旅程只支持累计资源说明，最后 ready_ms 只对应系统页导航。B1 完整旅程 API transfer 少 949 B 的差异单列，没有归因为资产节省。

HTTP 独立检查确认 830 条冷入口资产响应均为 200 且没有缓存命中标记；1,205 条资产响应没有 Content-Encoding 或 Cache-Control；15 个热样本资产 transferSize 均为 0。不能据缓存标记确定具体缓存层。离线 gzip 估算不代表实际 HTTP 传输。

`recovery-r1-paint-review.json` 核对全部 93 条记录与冻结工具哈希。108 个独立文档对应 213 个就绪快照，其中 195 个 stages 快照和 18 个独立 preview 快照，全部 observed。冷/热目标六组 FCP 各 5/5。33 个快照补采取得就绪时尚未发布的 FCP；1 个原生 FCP 确实晚于就绪终点，按实际时间保留。等待为 0–6.8 ms，没有 timeout、unsupported 或 error。213 不能解释为独立 FCP 样本数。

冻结工具 SHA-256：

- browser_probe.mjs：`3ae70bc5884653d1aeb29dda42c81221af0b4bf64bc1bf43874419d25b9b80dd`。
- measure.mjs：`e5b7f96d90898082450b2c76d688fa8e4838101c57905af52e618919477d45cd`。

当前采集目录和样本均绑定这两个哈希。旧目录若没有 instrumentation sidecar，工具本身没有完整的拒用保障；本次最终目录为新建目录，全部样本已逐一核对，因此该通用工具限制不构成本次验收阻塞。

## 门槛、范围与最终清理

| 检查 | 结果 |
| --- | --- |
| 三方案前端门槛 | B0 check/build attempt 4、test attempt 3，35 项通过；B1/B2 check/build attempt 3、test attempt 4，39/42 项通过。原有 27 项测试保留。复用未变更产物的通过记录，没有机械重复运行。 |
| 检查脚本 lint/format | reviewer 脚本的 Ruff check 和 Ruff format --check 通过。 |
| 检查脚本类型 | Pyright 通过。 |
| 测量工具回归 | 8 项 paint 收集确定性检查通过；8 项累计资源断言通过。未降低原门槛或修改样本。 |
| 任务上下文 | `task.py validate` 的 implement/check 清单各 12 条通过。 |
| Git 与产品范围 | git diff --check、git diff --cached --check 通过；289 个跟踪文件逐字节保持，暂存路径、任务外未跟踪路径、私有目录跟踪路径均为 0。 |
| 受保护路径 | 原 web/dist 文件集合与哈希、launch 配置哈希保持；缓存备份只检查存在性，未遍历或读取内容。 |
| 合成环境与服务 | 独立检查 34 个夹具的哈希、长度、mtime 和路径集合保持；9000 连接拒绝为 10061，模型缓存为 0 文件，无暂扣资产。 |
| 最终任务材料 | `recovery-r1-artifact-audit.json` 为最终文件集合、UTF-8、JSON/JSONL、后缀和尾空白检查；文件数以该快照为准。 |

主会话的 `../visible/cleanup-after-matrix.json` 和生命周期记录说明预检、主矩阵、旅程的 19 个自有服务均退出。可见浏览器已回到 about:blank、恢复默认视口并关闭任务标签。检查代理审阅这些可见操作记录，没有独立操作浏览器、重开服务或新增截图。

## 未修复问题与边界

无未解决的本任务问题。产品实现与规范未变，未暂存、提交、归档、推送、创建任务或发布。没有读取私有数据、运行真实实验、训练、入库、权重或 GPU 验收。

结果仅覆盖本机 Edge、合成数据和环回网络；390 px 检查证明布局与交互，不证明手机性能。没有整机网络隔离、真实用户访问权重、公网表现或库级 CPU 归因证据。就绪指标包含观察器成本及稳定动画帧；FCP 可能来自加载中界面。报告已明确这些限制。

旧版 `independent-review.md`、`continuation-*-review.json`、原始采集分析及首次失败记录继续保留，作为版本演进证据；最终结论由本文和 recovery-r1 证据支持。
