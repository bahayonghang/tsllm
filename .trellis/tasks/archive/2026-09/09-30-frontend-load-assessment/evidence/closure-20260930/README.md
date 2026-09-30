# 旧前端加载评估本地收尾

日期：2026-09-30（America/Chicago）。本目录记录旧评估任务的证据复核、本地提交与独立归档准备。收尾准备完成不表示工作提交或归档已完成；最终状态由主会话的提交、归档和独立终审记录确定。

## 本轮授权与责任

用户本轮明确授权将旧评估规划、工具、原始观测、首次失败和决策证据定向暂存、本地 Conventional Commits，再执行正式独立归档。旧 `prd.md`、`report.md`、`verification.md`、`implement.md` 和 `task.json` 中的旧授权范围保留为采集时事实。本轮授权另记于 `task.json` 的 `closure_20260930` 字段。

本轮产品写入范围为空。当前 B1 产品保留；不实施 B2、压缩、缓存或服务端优化。依赖、锁文件、生成类型、构建配置、B1 冻结证据、其他任务原件、原 `web/dist` 和 `.claude/launch.json` 保持只读。私有 `data/`、`ref/`、`runs/`、`cache/` 及备份不读取。

本轮不运行服务、浏览器、真实实验、训练、入库、作业提交、权重下载、依赖安装、网络或防火墙修改。原始证据引用的临时目录不作为本轮输入。任务工具只读取仓库内保留材料或指定 Git 对象。

主会话负责 Git、归档和会话日志；research 负责材料梳理；independent checker 负责独立验收。preparation 负责固定文件审查、字节副本、授权记录及引用适配。共享工作区内各代理按所有权写入，不撤销其他代理修改，不递归派发。

## 两个基线和两组测量

| 用途 | 基线或来源 | 复核口径 |
| --- | --- | --- |
| 历史评估 | `e9ce26a7bd1a4ed67cd30d257354e7345c44dec1` | 旧 289 文件工作树快照、B0/B1/B2 补丁、清单、图、门槛、采集器和 recovery-r1 原始观测 |
| 本轮产品保护 | `1b075dc99b5fd4d5174809fe7f3416717c5d0584` | preflight 的 586 个跟踪文件及 3 个受保护文件，归档前全部保持 |
| 已实施 B1 | 产品提交 `934ba580e39a3ecee53abe936cc41ff5aaef0049`；归档提交 `40648784376a5d3dc165e75f2aa981f9843722c4` | 本轮保护当前 B1；原 B1 任务冻结证据只读 |

工作分支保持 `codex/frontend-route-lazy-loading`。`task.json.branch`、`base_branch` 和原 `meta` 保留旧评估分支和实验事实，不据旧字段切回旧产品。

旧评估最终结论对应 recovery-r1 的 90 个主观测和 3 个完整流程。原修订的 90 个主观测、6 个预检、3 个流程，以及 recovery-r1 的 2 个预检均保留。B1 正式实施的 60 个主观测和 2 个流程属于已归档的另一任务，不混入旧评估。旧 225.0 ms 和旧百分比保持历史含义，本轮没有新增实测。

历史 `baseline-tracked-sha256.json` 保存工作树字节；Git 对象保存仓库字节。独立检查首次将两种口径要求为完全一致，出现 4 项失败。已保存首个脚本及失败命令，第 1 轮修正仅明确以下 4 个非产品文件的 LF→CRLF 关系：

- `.trellis/spec/guides/code-reuse-thinking-guide.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`
- `.trellis/spec/guides/index.md`
- `.trellis/tasks/archive/2026-09/00-bootstrap-guidelines/task.json`

其余 285 个历史 SHA-256 与 e9 Git blob 精确一致。上述 4 个 Git blob 均不含 CR；逐个将 LF 替为 CRLF 后，SHA-256 严格匹配各历史记录。双哈希、字节数和替换行数保存在 `preparation/repair-r1/closure-evidence-v1.json`。该工具只允许这 4 个固定路径，不对其他差异进行通用换行忽略。历史证据保持原字节。

## 固定材料审查

`preflight.json` 固定原 463 个文件，总计 32,877,915 B。`preparation/material-audit.closure-v1.json` 逐文件保存用途、SHA-256、大小、UTF-8、CRLF 和原始空白信息。全部匹配原快照；320 个 JSON、2 个 JSONL 结构解析通过；所有文件为文本，未发现二进制或凭据模式命中。

审查范围包括规划、合成夹具生成器、采集器、原始计时和资源记录、依赖图、补丁、门槛日志、失败、报告与独立检查。合成来源由任务内 `evidence/fixtures/create_fixtures.py` 的确定性生成逻辑和观测中的合成标识支持。未运行夹具生成器，未读取该工具旧路径指向的私有或临时文件。类型和模式扫描属于辅助检查，独立终审仍须覆盖用途与来源。

超过 1,000,000 B 的文件只有以下两份；用户已授权保留完整原始证据，审查后按本任务范围纳入历史。

| 文件 | 大小 B | 结构与用途 |
| --- | ---: | --- |
| `evidence/report/original-recomputed.json` | 1,915,287 | original 的构建清单、90+3 观测派生统计、21 组、完整 URL 集合、差值和版本哈希 |
| `evidence/report/recomputed.json` | 1,915,231 | recovery-r1 的相同结构；与原修订分别保留 |

两份 JSON 各检查 40,792 个标量值、4,300 条 URL 字符串，URL 主机均为 `127.0.0.1`。没有私有数据文件或构建资产正文。归档保留清单和历史哈希绑定；本轮只能重新汇总离线 gzip 清单值，不能重新压缩未保存的构建资产。

## 原始副本与空白

`preparation/log-preservation.closure-v1.json` 将 38 份被 Git 忽略的服务 `.log` 映射到 `preparation/logs/` 下的 `.log.txt` 副本。原路径、SHA-256、大小、mtime 与 Git 可追踪性均有记录。38 份原日志均为 0 B；空日志不证明服务退出，退出结论仍依据历史 lifecycle 和清理证据。

原 `task.json` 在新增本轮授权字段之前保存为 `preparation/task-before-closure.json`，大小 1,212 B，SHA-256 为 `f6a25f3d9ba1e6cacd548fcb9fddbe1126d4f0abc653457ba458904c51fef883`。`task-before-closure-fingerprint.json` 记录该副本与 preflight 的一致性。原 implement/check 清单另有 `reference-adapters/assessment-*.before-archive.jsonl.txt` 字节副本，供归档后的直接自引用适配追溯。

任务根 `.gitattributes` 随目录归档，使用 `-text` 保留证据原字节；仅将 CRLF 识别为合法行尾，保留 `blank-at-eol`、`blank-at-eof` 和 `space-before-tab`。仓库根 `.gitattributes` 不变。

原有三个 `instrument/validation-1-command-{1,2,3}.txt` 含末尾空行，原样保留。主会话必须保留完整 `git diff --cached --check` 输出，并分别报告原始日志/补丁告警与代码、文档、工具检查。不得删除日志空白、屏蔽默认空白项或把带告警的完整检查表述为通过。新增工具首次 Ruff check 的 14 项 E501 和 format 检查失败保存在 `preparation/static-initial-{1,2}.json`；格式修正后的检查通过。

## 归档路径与冻结引用

直接路径映射为：

```text
.trellis/tasks/09-30-frontend-load-assessment/
→ .trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/
```

`preparation/reference-adapters/mapping.closure-v1.json` 记录 4 份清单的原 SHA-256、大小、逐条 old→new、目标文件哈希和新清单哈希。B1 的 implement/check 清单各有第 9–13 行共 5 条旧评估引用；保留 B1 冻结原件，只显式使用 `b1-implement.closure-v1.jsonl` 和 `b1-check.closure-v1.jsonl`。

旧评估自身 implement/check 清单各有 1 条 `research/baseline-findings.md` 自引用。归档后仅替换该直接路径，使默认 `task.py validate` 可用；适配目标保存在 `assessment-implement.closure-v1.jsonl` 和 `assessment-check.closure-v1.jsonl`。不创建带 `task.json` 的伪任务。其余历史报告、原脚本、日志和绝对临时路径保持原文，复核通过新版本工具的自身位置定位。

## 复核命令与收尾顺序

新增准备工具的 `--verify` 模式只读，支持活动目录和归档目录，核对 463 个历史文件、38 个日志副本及 50 条清单目标。独立工具支持 `--output`，避免覆盖首次失败。以下命令使用归档后路径；归档前将任务路径替换为活动路径。

```powershell
.venv/Scripts/python.exe -B .trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/evidence/closure-20260930/preparation/prepare_closure_v1.py --verify
.venv/Scripts/python.exe -B .trellis/scripts/task.py validate .trellis/tasks/archive/2026-09/09-30-frontend-load-assessment
```

1. 对 AC1–AC6、原始数值、同修订、保护范围和新增材料完成全范围独立终审。版本绑定门槛与可见验收按已记录范围复用。
2. 主会话核对完整状态和范围，再定向暂存旧任务规划与全部证据；核对暂存 blob、字节、范围及完整空白输出。本轮产品改动为 0。
3. 创建工作提交，确认旧任务和已有 B1 产品/规划均进入 Git 历史。
4. 确认同名归档目标不存在、没有活动子任务，且其他 archive 子树无脏文件。执行用户指定的正式 `task.py archive` 命令；自动提交失败立即停止。归档提交独立，不能混入其他任务或产品。
5. 对归档后的同一任务更新上述 2 条直接自引用，校验映射和默认 `task.py validate`；主会话记录归档结果及后续引用提交。
6. 按 `trellis-finish-work` 记录会话并引用工作提交。日志阶段只允许明确的 journal/index 变化；不因此忽略其他 preflight 文件变化。最终交付提交哈希、归档路径、限制及未推送状态。

## 上下文与检查状态

使用原生 SubagentStart 注入；28,008 tokens 的显示结果被截断后读取保存文件并分段补读。旧 `report.md` 37,508 B 超过单文件注入上限，已单独全文补读。AGENTS、适用规范、Phase 2.1/2.2、父任务共享契约、旧任务及已归档 B1 报告/验收/closure 材料均已核对；未发现适用的嵌套 AGENTS 或 CONTEXT 文件。

`preparation/repair-r1/command-1..12.json` 记录新增三脚本的 Ruff 格式、Ruff check、format --check、Pyright、固定材料准备、只读验证和受影响 closure/source-replay 验证，退出码均为 0。已通过的专用数值、HTTP 和 paint 检查没有重复运行。首次不存在文件的只读查找另存 `preparation/read-command-failure-1.json`。

同一轮 F2 修正了源码重放工具对两种历史结构的误判。B0 的 `reproduction-check.json` 只有 `reproduced_files=51`、空 `mismatches` 和测试文件不变摘要；工具核对 B0 前后补丁哈希相同及 `source_changes` 哈希，不声明完成不存在的 51 文件逐项明细复算。B1/B2 的 recovery-r1 记录有逐文件明细，纯内存应用 e9 Git blob 与任务内补丁后分别核对 53/55 个文件哈希通过。结果为 `preparation/repair-r1/source-replay-v1.json`。未生成源码副本、构建资产或访问临时目录，首次 KeyError 与原工具由 independent 目录保留。

本轮不产生产品或共享契约新知识。主会话的 trellis-update-spec 检查结论为无需修改规范。准备材料不代替 checker 的独立终审，也不预先声明提交、归档、服务检查或 Git 对象核对完成。
