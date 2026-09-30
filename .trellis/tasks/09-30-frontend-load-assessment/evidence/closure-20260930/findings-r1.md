# 收尾检查第 1 轮反馈

日期：2026-09-30。反馈来自独立 `trellis-check`；主会话回灌同一任务。最多允许 3 轮同范围返修，本轮未扩大产品范围。

## F1：历史工作树快照与 Git 对象的行尾口径

新工具 `independent/closure_verify_v1.py` 首次执行在历史基线断言处退出 1。记录为 `independent/closure-evidence-command-1.json`。285 个文件与 e9ce26a 的 Git blob 原字节相同；另 4 个非产品文本的历史快照使用 CRLF，Git blob 使用 LF：

- `.trellis/spec/guides/code-reuse-thinking-guide.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`
- `.trellis/spec/guides/index.md`
- `.trellis/tasks/archive/2026-09/00-bootstrap-guidelines/task.json`

独立检查已确认上述 Git blob 转为 CRLF 后 SHA-256 严格等于历史 manifest。原断言把两种字节口径混为一项。该失败未发现产品或观测变化。

修正要求：`trellis-implement` 仅修改该新增检查脚本，枚举这 4 个历史例外，记录 Git 原字节和 CRLF 候选的 hash、历史 hash 及等值判断；其他路径仍须原字节一致。不得使用通用行尾规范化忽略未知差异，不得修改旧 manifest 或原始文件。checker 保存失败源码字节副本和 hash。只重跑受影响的 closure 验证及该脚本的静态检查。

## 已通过及保留事项

旧数值/HTTP/paint 工具的任务内重跑已通过，结果写在新 independent 目录：90 个主观测、3 个完整流程，1,349 与 302 项统计/差值，2,244 条资产记录；830 条冷响应、1,205 条无压缩响应、213 个就绪快照和 108 个独立文档一致。该轮不重复上述检查。

checker 曾因 `stream disconnected before completion: Concurrency limit exceeded for user, please retry later` 中断。研究代理完成后，主会话续接同一 checker。该事件为代理传输失败，不计为实验失败或检查通过。

本轮最终全范围独立结论、静态结果和修正后的 Git 比较证明仍以 independent 的后续报告为准。

## F2：B0 历史重现摘要的结构适配

checker 新增纯内存源码补丁重放工具，用 Git e9ce26a 对象和任务内 patch 加强来源绑定。首次执行因 B0 初版 reproduction-check.json 使用 `reproduced_files`/`mismatches` 摘要，误按 B1/B2 recovery-r1 的 `all_equal`/`files` 明细读取而出现 KeyError。失败源码和 `source-replay-command-1.json` 保留。

本轮将该新增工具 `independent/replay_sources_v1.py` 交同一 trellis-implement 修正：B0 核对 before/after patch 一致、历史 51 文件摘要及空 mismatches；B1/B2 在内存应用 patch 并逐文件核对 53/55 个历史哈希。必须披露 B0 无初版逐文件明细，不能构造该证据。不输出源码副本，不读取旧临时目录，不重新构建。修正后仅运行受影响工具与静态检查，随后由 checker 做最终全范围复核。
