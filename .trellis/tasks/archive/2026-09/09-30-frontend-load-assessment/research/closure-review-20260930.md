# Research: 旧加载评估的证据复核与独立归档

- Query: 核对旧评估 AC1–AC6、recovery-r1 原始证据、复算工具、失败保留和归档路径，给出不改变当前 B1 产品的收尾方案。
- Scope: internal；仅写本研究文件，其余文件只读。
- Date: 2026-09-30（America/Chicago）

## Findings

### 1. 结论与责任边界

现有材料支持继续执行证据复核和本地收尾。研究未发现需要重新测量或修改产品才能解释的数值冲突。独立 checker 的全范围复核、主会话的 Git 对象核对及归档结果仍为后续完成条件。本研究不代替这些步骤。

历史评估基线为 `e9ce26a7bd1a4ed67cd30d257354e7345c44dec1`。主会话派发时的当前 HEAD 为 `1b075dc99b5fd4d5174809fe7f3416717c5d0584`，工作分支为 `codex/frontend-route-lazy-loading`。后两项来自主会话派发，本研究未执行 Git 命令。旧 `task.json` 的 branch/base_branch/experiment_root 属于历史执行信息，不能据此切回旧产品或读取原临时目录。

当前产品确有七条 lazy 路由和同步 AppLayout，见 `web/src/router.tsx:1–61`；恢复操作执行 preventDefault 和 location.reload，见 `web/src/components/RouteLoading.tsx:9–29`。当前产品保护必须使用本轮 B1 快照，历史 289 文件不变检查仅支持当时的评估边界。

研究已完整读取旧 `report.md` 的 394 行、`verification.md`、`evidence/review/continuation-review.md`、方案修订和 instrument 说明、父任务 PRD/共享设计，以及归档 B1 的 report/verification/closure 说明。没有使用被截断的 report 注入替代全文。未找到根 CONTEXT.md 或研究范围内额外的嵌套 AGENTS.md/CONTEXT.md。

### 2. 文件与证据索引

以下未写仓库前缀的路径均相对于 `.trellis/tasks/09-30-frontend-load-assessment/`。

| 文件或目录 | 作用与已核对事实 |
| --- | --- |
| `prd.md`、`design.md`、`implement.md` | 定义 3×6×5 主矩阵、资源窗口、行为门槛、保护范围和实施历史。 |
| `report.md:1–394` | 最终 recovery-r1 决策、18 组完整范围、资源/传输/gzip 分列及全部局限。 |
| `verification.md:11–18` | AC1–AC6 到证据的对应表。 |
| `evidence/review/continuation-review.md:13–20` | 既有独立检查结论及每项复核范围。 |
| `evidence/measurement/recovery-r1/raw/` | 90 个有效主观测；order/lifecycle 为控制记录，不能加入观测分母。 |
| `evidence/measurement/recovery-r1/journey/` | 3 个完整访问流程，每方案 1 个；最后 ready 时间只代表系统页导航。 |
| `evidence/measurement/recovery-r1/*-instrumentation.json` | raw、journey、pilot 的工具修订及 SHA-256 sidecar。 |
| `evidence/measurement/recovery-r1/instrument/` | 修订前后采集脚本、原始矩阵快照、patch、8 项确定性测试、syntax/lint 首失败和成功记录。 |
| `evidence/variants/recovery-r1/before/`、`after/` | 方案恢复修订前后 patch、清单、图、源快照和工具；两个修订不能混算。 |
| `evidence/variants/recovery-r1/reproduction-check.json` | 保留 B1 53 文件、B2 55 文件逐字节重现结果。 |
| `evidence/variant-gates/` | 31 个门槛 JSON 及对应 31 个文本日志；成功和首次失败均保留。 |
| `evidence/visible/observations.md`、`continuation.md` | 可见浏览器双视口、真实 Canvas、表单预览、七类警告和恢复证据。 |
| `evidence/report/recomputed.json` | 93 条原始 SHA、21 组统计、2,277 项既有报告统计核对及复算脚本 SHA。 |
| `evidence/report/original-report.md`、`original-recomputed.json` | 原修订结果，须与 recovery-r1 同时保留。 |
| `evidence/scope/`、`evidence/review/recovery-r1-scope.json` | 当时 e9ce26a 基线、原 dist/launch 和任务边界证据。 |

### 3. AC1–AC6 的可复用证据

| AC | 可复用依据 | 本轮应完成的复核 |
| --- | --- | --- |
| AC1 | variants 清单、图、补丁、重现及 variant-integrity；HTTP 原始响应和 header 复核。 | 检查历史基线标识、patch/graph/inventory 绑定和历史验证哈希；保留构建/依赖限制。 |
| AC2 | recovery-r1 90 个主记录、order/lifecycle 和完整 summary。 | 独立计数 18 组各 5 条、valid、attempt、身份唯一、交替顺序，不混入 pilot、旧矩阵或 B1 正式实施数据。 |
| AC3 | 原始 Navigation/Resource Timing、独立 numeric/http/paint 结果和 recomputed.json。 | 复算所有中位数、min/max、URL 并集、重复请求 transfer；gzip 从逐文件清单加总并绑定历史原产物复核。 |
| AC4 | B0 check/build-4、test-3；B1/B2 check/build-3、test-4；双视口正常行为与实际恢复。 | 复用相同版本的完整门槛和可见验收，核对日志与产物/修订归属，不启动新构建或浏览器。 |
| AC5 | report 的收益、首次使用成本、全程资源、B2 不采用理由和局限。 | 保留历史结论；新收尾材料注明本轮为证据复核，无新增性能实测。 |
| AC6 | 历史独立数值/范围/清理；34 合成夹具不变，19 自有服务退出、视口与标签清理。 | 本轮 B1 保护快照、任务材料/Git 对象范围、独立终审、归档路径与会话日志。 |

AC4 最终测试数为 B0 35、B1 39、B2 42；原有 8 个测试文件与 27 项测试保留。入口/加载中、导入失败、实际点击重载和深链接均有对应检查。B1 正常页面复用恢复修订前的正常行为，恢复补丁只改变错误恢复动作；修订后另有实际路由恢复和完整性能矩阵。B2 正常行为使用修订后产物。依据：`report.md:328–347`、`verification.md:40–48`。

### 4. 本研究执行的只读核对

直接解析 recovery-r1 raw/journey 的 93 个 JSON，确认 90 个主观测及 3 个旅程，93 个 variant/scenario/sample 身份唯一，全部 valid=true、attempt=1。raw/journey sidecar 完全相同；每条 instrumentation 与所在目录 sidecar 一致。

两份冻结采集脚本的 SHA-256 同时匹配 instrument/after、measurement 根和 sidecar：

- browser_probe.mjs：`3ae70bc5884653d1aeb29dda42c81221af0b4bf64bc1bf43874419d25b9b80dd`。
- measure.mjs：`e5b7f96d90898082450b2c76d688fa8e4838101c57905af52e618919477d45cd`。

recomputed.json 中 93 个原始 SHA 全部与当前文件匹配。report.md SHA 为 `a23ad2bfc48bf5ef233d279295accaaf46c6772f7bc2124f4440412276494f9a`，与 continuation-review 的终审记录一致。复算脚本 SHA 为 `79d96ca669e3cabbfbede318ac2c51405aa436e54f102c533b07e16e40a550d6`，与 recomputed.json 一致。恢复修订 before/snapshot.json 的 17 份方案材料及 46 份既有门槛文件 SHA 全部匹配；instrument/before/snapshot.json 的 2 份旧脚本及 92 份原 raw/控制记录 SHA 也全部匹配。

18 组时间直接从原始 primaryReadyMilliseconds 重新计算，n 均为 5；中位数和完整范围均匹配 report.md:133–150。冷入口中位数 B0/B1/B2 为 303.8/225.0/227.6 ms。B2-first-forecast-s3-a1 的 2,439.7 ms 仍在有效样本中；B2 该组范围为 1,425.5–2,439.7 ms。原因未查明，没有删样或补采。

B0/B1/B2 顶层 patch、inventory、graph 与 recovery-r1/after 逐字节一致；patch SHA 与各 inventory 一致。图中所有 chunk、imports 和 dynamicImports 均落在对应资产清单。共 62 个文件（含 HTML），数量 2/21/39；正文总量为 2,420,191/2,430,585/2,442,905 B；逐文件 gzip 字段加总为 776,665/796,118/810,268 B，均与清单总量一致。

历史 reproduction-check 的 B1/B2 53/55 行均为 equal=true，原 hash 与 reproduced_hash 一致。本研究没有重新导出源码或构建产物。独立 checker 应继续核对旧 Git 基线与 patch/source 元数据的绑定。

### 5. 工具适配与执行限制

| 工具 | 当前行为 | 本轮处理 |
| --- | --- | --- |
| `evidence/review/verify_numerics.py:81–102,148–242` | 显式读取 raw、summary、variants；重算资源窗口、分组统计、差值。只写指定 output。 | 可重跑到新的收尾输出，main 与 journey 分别调用，旅程使用 supplementary-only。 |
| `evidence/review/verify_http.py:10–75` | 只读 raw 和 inventory，核对冷入口状态/长度、编码、缓存和热传输。 | 可重跑到新的收尾输出。 |
| `evidence/review/verify_paint_revision.py:20–90` | 读取任务内 measurement 根脚本、raw/journey sidecar 和样本。 | 可按原路径执行并指定新 output；移动脚本副本时必须显式适配脚本定位。 |
| `evidence/report/recompute_report.py:179–185,653–666` | 默认读取 original measurement；会同时重写 JSON 与 report 的生成区域。 | 禁止使用默认参数直接运行；需要复用时显式 recovery-r1 输入，并把 report/output 指向有新版本标识的任务内副本。 |
| `evidence/review/verify_variants.py:18–77` | 读取原 experiment-root/source、variants/B*/web/dist；要求相同 Python/zlib，再压缩产物。 | 不读取原临时树，不重建。适配检查仅核对保留清单/图/patch/历史成功记录。 |
| `evidence/review/verify_cleanup.py:10–34,47–48` | 从 task.json 读取临时 experiment_root，访问夹具/模型目录且覆盖旧结果。 | 不运行；复用任务内生命周期和清理记录。本轮若核对资源，只检查本轮自有资源。 |
| `evidence/scope/verify_scope.py:27–34,64–77` | 要求 HEAD=e9ce26a、旧分支、289 文件全部不变、无任务外新增文件。 | 不用于本轮；新增收尾范围检查以当前 B1 快照及明确允许文件为依据。 |
| `evidence/review/continuation_audit.py` | 对旧任务固定材料集合审计并写旧结果。 | 新闭环材料用独立版本审计，不能覆盖历史文件数或既有结果。 |

collectPaint 保留原就绪终点，额外等待单列；代码在 `instrument/after/browser_probe.mjs:164–200`、`measure.mjs:79–81`。sidecar 比对和样本拒绝覆盖见 `measure.mjs:204–224`。旧工具在已有无 sidecar 目录下仍有通用混版防护不足；最终 recovery-r1 目录为新目录，93 条身份已逐一核对，该限制不改变本次历史数据结论。

任务没有保留构建包，符合原 PRD R3.4。保留清单和历史 variant-integrity 支持复算离线 gzip 总和及其版本依据；本轮没有源产物字节可供重新压缩。不得把清单加总写成“重新压缩产物通过”。如果验收改为必须现场重建或重新压缩，现有授权下应停止并列明缺口。

### 6. 失败与高值的保留清单

- `evidence/variant-gates/B0-{check,test,build}-1.*`：pnpm 自动准备与 junction 冲突；B0-check/build-2 为 originalLength 类型错误，B0-check-3 为格式问题。全部原日志存在。
- B1/B2-test-1：lazy 拒绝/空 Outlet 及原超时；没有删除原测试或提高超时。
- B1-test-3 为 2 failed/37 passed，B2-test-3 为 4 failed/38 passed；test-4 分别 39/42 passed。实际点击恢复缺陷先失败再修复。
- `evidence/visible/module-failure.json` 保留 recovery_observed=false；两份 module-recovery-r1 记录保留恢复后的相同资产 SHA、完整 URL 与成功状态。
- `instrument/before/`、paint-collection-analysis、lint-1/2、validation-1 保留原生 FCP 收集时序缺陷、stdin lint 首次失败及确定性复验。
- reproduction-check-initial、continuation-artifact-audit-initial、cleanup-command-failure、cleanup-review-initial 保留 CRLF/审计后缀/命令/socket 初次失败。
- 原矩阵、原报告和所有 pilot 保留，最终 90+3 不与原始 90+3 或 B1 正式实施 60+2 混算。

采集修订说明记载历史 lint 日志曾规范化换行和尾空白，见 `instrument/README.md:35`。本轮应保留现有历史字节，不进一步修剪，也不把历史日志声称为未经任何规范化的原终端字节。

### 7. 文件保真、大文件与敏感边界

研究开始的目录清点为 465 文件、33,148,166 B，其中包含主会话已新增的两个 closure-20260930 文件；历史 B1 冻结记录为旧评估 463 文件，不能把新增收尾材料计入当时的分母。

38 个 `.log` 全部为 0 B，被根 `.gitignore` 的 `*.log` 规则忽略；其中 recovery-r1 为 pilot 1、raw 15、journey 3。建议逐个保存任务内 `.txt` 字节副本，映射原相对路径、SHA-256 和大小。空日志不能证明服务退出，退出依据仍是 lifecycle 与 cleanup。不得 force-stage `.trellis/`。

两个超过 1,000,000 B 的原文件为 `evidence/report/original-recomputed.json`（1,915,287 B）和 `recomputed.json`（1,915,231 B）。两者为可解析 UTF-8 JSON，保存原始 SHA/URL/统计，属于本次需要保留的完整证据。任务文件检查未发现非 UTF-8 文件或字面 NUL 字节；没有构建包、截图或二进制候选。research 角色未加载 implement.jsonl/check.jsonl 内容，清单验证由主会话/checker负责。

根 `.gitattributes:3` 使用 text=auto eol=lf，直接暂存会改变 CRLF 原始证据。归档 B1 的 closure/README.md:37–41 已保留同类首次字节失败及任务内 `-text` 处理。旧任务可采用局部字节保真规则，随后逐个比较索引/Git blob 与工作区 SHA。保留完整 diff --check 的原始输出；原日志空白与新代码/文档/工具空白分别披露。

未访问私有 data/ref/runs/cache 或备份内容。以上敏感边界结论只覆盖本研究访问范围；大文件与所有最终暂存候选仍需独立检查。没有在研究中启动服务、浏览器、作业、训练、入库、下载、安装或构建。

### 8. B1 已归档交付与直接路径映射

归档 B1 的 `evidence/closure/result.md:5–12` 和 archive-receipt 记录工作提交 `934ba580e39a3ecee53abe936cc41ff5aaef0049`、独立归档 `40648784376a5d3dc165e75f2aa981f9843722c4`。工作提交覆盖 5 个产品文件、2 份规范、289 个任务文件；归档只移动该任务并更新状态/日期。这些为已保留的交付记录，主会话仍须用 Git 对象核对。

B1 的 report.md:17、:27、:98 明确使用 60 个主观测和 2 个流程，冷入口为 234.0 ms；旧 225.0 ms 仅为历史评估。两个任务即使资产字节相同，也不能复用时间样本或混合分母。

预期映射为 `.trellis/tasks/09-30-frontend-load-assessment/` → `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/`。在本任务新增映射说明，保留冻结证据的历史字符串。归档 B1 的 postarchive-validation.json 已证实其两个上下文清单引用旧 report 路径；本研究未读取这些 role-isolated 清单。B1 的 `tools/preflight.py:34`、`evidence/review/audit_scope.py:80` 也包含旧评估路径。

当前 `.trellis/spec/` 和 `.trellis/workspace/` Markdown 定向检索未发现旧评估完整目录名的直接引用。B1 冻结脚本、旧 gate 命令、原始快照和日志中的路径保持历史原文。不得批量改写 B1。需要可执行的归档复核时，创建任务内新版本适配副本，并记录源 SHA、路径替换和验证结果。B1 清单若在旧任务移走后不能按原路径 validate，应作为冻结清单的历史路径限制明确记录，由主会话按直接映射边界处理。

### 9. 建议的闭环顺序

1. 以当前 B1 快照为保护基准，确认原 dist/launch、B1 冻结证据及范围外脏文件的状态；历史任务 metadata 不驱动分支切换。
2. 在同一任务新增收尾说明、日志副本映射、字节保真配置和必要工具适配；保留全部旧验收文件及 SHA 绑定。
3. 独立 checker 读取 recovery-r1 90+3，重算统计/URL/transfer/清单 gzip，检查历史 patch/source/产物/sidecar和门槛/可见证据；发现材料问题仅修复同范围副本。
4. checker 终审通过后，定向暂存旧任务规划、工具、原始观测、失败与收尾材料；核对完整候选、大小/二进制/敏感项、索引字节和 Git 对象。
5. 工作提交完成且 B1 产品及规划已在历史中后，确认同名归档目录不存在、没有活动子任务，再运行用户指定 task.py archive。自动提交失败时停止，不继续伪装完成。
6. 独立检查归档提交只包含本任务路径迁移与任务 metadata 更新；后续引用映射和会话日志单独记录工作提交，不混入产品改动。

## Related Specs and References

- `.trellis/workflow.md:234–241,484–555`：首行 Active task 派发协议、原生注入及 implement/check 职责。research 不递归派发。
- `.trellis/spec/frontend/quality-guidelines.md:9–24,37–46`：正式三门槛、资源/时间分列、真实恢复和双视口检查。
- `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md:24–29,328–351`：服务不导入模型、共享 API 契约；本次不改共享契约。
- `.trellis/tasks/archive/2026-09/09-28-tsfm-platform/prd.md:71–78,111–117`：私有目录/离线边界和已批准的进程级隔离范围。
- 外部资料：本研究没有新增网络来源。历史 Node、pnpm、Vite、Python、zlib、Edge、Playwright 版本见旧 report.md:27–38；版本为采集时环境证据，不声明当前重新测得。

## Caveats / Not Found

- 没有新性能测量、重新构建、重新 gzip 压缩或新可见验收。现有历史完整门槛按版本证据复用。
- 依赖没有完整事前/事后哈希；本机环回、合成数据、n=5、旅程 n=1、FCP 可来自加载态、无库级 CPU 归因等限制保持，不能扩大为公网/手机/真实用户结论。
- 本研究未执行 Git、暂存、提交、归档或 task.py validate；没有确认最终工作区/索引/归档状态。最终状态由主会话和独立 checker 记录。
- 目前未发现需要新实验才能解决的证据冲突。若独立检查发现原始记录/版本缺失、源对象不匹配或共享契约冲突，应停止受影响工作，不能补造。
