# 旧前端加载评估收尾结果

日期：2026-09-30，America/Chicago。工作分支保持 `codex/frontend-route-lazy-loading`。本轮产品写入范围为空，未推送或发布。

## 提交与归档

| 项目 | Git 对象及结果 |
| --- | --- |
| 开始快照 | `1b075dc99b5fd4d5174809fe7f3416717c5d0584` |
| 旧评估规划和证据提交 | `967644734806d9056af67fcc7c284d5147b9f97e`，530 个文件，全部限定旧任务 |
| 独立自动归档提交 | `60fc52f7b46b205181b2c83f697b3b2628bfca18`，直接父提交为工作提交 |
| 已有 B1 产品 | `934ba580e39a3ecee53abe936cc41ff5aaef0049`，保留于祖先历史 |
| 已有 B1 归档 | `40648784376a5d3dc165e75f2aa981f9843722c4`，保留于祖先历史 |

实际执行 `.venv/Scripts/python.exe -B .trellis/scripts/task.py archive .trellis/tasks/09-30-frontend-load-assessment`，退出码为 0，自动提交成功。没有使用归档失败回退、强制暂存或 amend。归档前无同名目标、活动子任务或范围外脏文件。

归档后路径为 `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/`。归档提交的 530 项中，529 项 blob 完全相同；`task.json` 仅将 `status` 从 `in_progress` 改为 `completed`，将 `completedAt` 从 null 改为 `2026-09-30`。历史 branch、base_branch、meta 和 notes 保持。归档提交不含产品、其他任务、引用修正或会话日志。

归档后 `task.py current` 退出 1、stdout 为空，表示没有当前任务。工作提交和归档提交完成后，完整 Git 状态分别为空。命令原输出、完整路径清单、Git 对象和字段比较见 `work-commit-v1.json`、`archive-v1.json`。

## 独立验收和证据边界

独立 trellis-check 的全范围结论见 `../independent/final-review.md`：AC1–AC6 通过，无未解决的范围内问题。第 1 轮修复 F1/F2 两项收尾工具问题，首次源码、失败输出和修复后结果均已提交，没有新增产品优化。

recovery-r1 的 3 方案 × 6 场景 × 5 次共 90 个有效主观测及 3 个完整流程通过独立复核。数值、URL 并集、实际传输、sidecar、脚本和历史产物绑定保持；报告的 40,275 个对照值一致。原 463 个文件、38 个字节相同日志副本和全部首次失败可追溯。B2 的 2,439.7 ms 高值保留，旧 225.0 ms 和旧百分比没有充当本轮新测量，也没有混入 B1 正式实施的 60 条观测。

历史核验使用 `e9ce26a7bd1a4ed67cd30d257354e7345c44dec1`；当前产品保护使用开始快照 `1b075dc99b5fd4d5174809fe7f3416717c5d0584`。B1/B2 的源码内存重放分别匹配 53/55 文件。B0 只有 51 文件的历史摘要，没有虚构逐文件明细复核。历史 285 项工作树 SHA 与 Git blob 精确一致；另 4 个固定路径有严格 LF→CRLF 双哈希证明。

历史 check/test/build 和 390/1280 px 可见验收按版本绑定证据复用。本轮没有重新实验、构建、压缩或打开浏览器。离线 gzip 仅对保存的逐文件值重新求和，B0/B1/B2 为 776,665 / 796,118 / 810,268 B；未保留的构建包不能重新压缩。38 份原服务日志均为 0 B，服务退出仍依据历史 lifecycle 和 cleanup。

结论限于历史本机 Edge、环回地址、合成夹具和既定观察器。完整流程每方案只有 1 次；390 px 仅支持布局与交互验收。没有总体置信区间、真实手机性能、库级 CPU 归因或整机网络隔离结论。依赖没有完整事前/事后哈希的原限制继续保留。

## 暂存、Git 对象和空白检查

`git-final-index-v3.json` 保存最终 530 项暂存路径、blob、SHA-256 和大小，全部与工作区逐字节一致。独立 checker 再次核对 530 项并确认可提交；确认记录保存在工作提交回执。工作提交 tree 与该快照完全一致。530 项清单已经包含独立终审报告和最终提交清单自身。

工作提交前，586 个原跟踪文件和 3 个额外保护文件全部匹配初始快照。归档后再次匹配。当前 B1 产品、根配置、依赖和锁文件、生成类型、B1 冻结证据、原 `web/dist` 和 `.claude/launch.json` 保持。后续会话日志只允许本次 journal/index 的明确变化。

本轮实际 `git diff --check` 和 `git diff --cached --check` 均退出 0，stdout/stderr 为空。原 instrument 输出的末尾空行和原始日志空白没有裁剪。材料中的原始空白说明与 Git 实际输出分别保留，没有套用 B1 归档的历史空白告警。新增工具的 Ruff、format 和 Pyright 通过；首次静态检查失败保留。

最终索引命令曾在创建进程前因传输字符串含 NUL 被拒绝。该次没有执行进程或写文件，改用原始字符串和 `chr(0)` 后成功。事件记录在 `git-final-index-v3.json`；该事件不属于性能实验失败。

## 直接路径映射和归档后验证

唯一目录映射为 `.trellis/tasks/09-30-frontend-load-assessment/` → `.trellis/tasks/archive/2026-09/09-30-frontend-load-assessment/`。归档后只更新本任务 implement/check 清单各 1 条 `research/baseline-findings.md` 自引用。原件保存在版本历史和 `../preparation/reference-adapters/assessment-*.before-archive.jsonl.txt`。

B1 冻结清单各有 5 条旧任务引用，原件保持历史文本。后续加载应显式使用本任务内 `b1-implement.closure-v1.jsonl` 和 `b1-check.closure-v1.jsonl`。`../preparation/reference-adapters/mapping.closure-v1.json` 记录 4 份清单、50 条目标以及原件和适配件哈希。历史报告、原脚本、绝对临时路径和冻结证据没有批量改写。

归档后的 `task.py validate` 通过 implement/check 各 12 项。归档后的 `prepare_closure_v1.py --verify` 只读核对 463 个历史文件、38 份日志副本、50 条引用，退出 0、写入 0。原输出和两条自引用的前后哈希见 `postarchive-checks-v1.json`。

本收尾记录、原始 Git 回执和两条引用修正使用归档后的独立文档提交保存。会话日志按 trellis-finish-work 记录，引用工作提交 `967644734806d9056af67fcc7c284d5147b9f97e`，不以归档提交代替工作提交。

本轮没有启动自有服务、创建浏览器标签或故障资产；没有私有数据读取、安装升级、网络配置、真实实验、训练、入库、作业提交或权重下载。无需修改共享契约或规范。建议保留当前 B1；任何 B2 或传输优化应另行获得范围与实验授权。
