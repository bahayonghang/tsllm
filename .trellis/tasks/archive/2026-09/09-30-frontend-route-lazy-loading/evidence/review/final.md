# B1 路由延迟加载独立终审

日期：2026-09-30。检查代理：/root/independent_check（trellis-check）。

结论：通过。AC1–AC10 的实现、正式门槛、可见验收、性能和清理证据一致。未发现未解决的范围内问题。产品返修轮次为 0。未暂存、提交、归档、推送或发布。

## Findings (fixed)

- File: evidence/review/audit_measurements.py。Issue: 审查脚本首次 Ruff 检查出现 6 处 E501。Fix: 仅调整表达式换行；保留 tool-gate-1.json，最终 Ruff、Pyright 和 3 个复算单测通过。
- File: evidence/review/audit_final_documents.py。Issue: 审查脚本 UTC 别名与导入格式不符合 Ruff 规则。Fix: 采用 UTC 别名并整理导入；tool-gate-22.json 保留失败，tool-gate-23/24/25.json 记录最终检查及 62 项核对通过。
- 没有产品修复。检查代理仅写入本任务 evidence/review/；产品由原 trellis-implement 完成。

## Findings (not fixed)

无未解决的范围内问题。以下证据限制已在 verification.md 披露：

- 可见恢复未取得 timeOrigin/navigation.type。实际链接点击、expectNavigation(waitUntil=load)、相同完整 URL 和恢复页面/Canvas 证明文档导航。产品先 preventDefault() 再 location.reload()；没有把 jsdom 替身作为真实重载证据。
- 首次实施测试的 GBK 日志错误使该次 Vitest 子退出码缺失；首次失败日志和外层退出 1 保留，同源码重跑记录子退出 1。最终正式门槛均退出 0，没有补造缺失退出码。
- 性能来自单机环回和合成终态夹具。暖入口未见就绪收益，精确原因未查明；版本、缓存及采集窗口核对未发现偏差。样本不足以外推真实部署的稳定收益。

## Verification

- Lint: pass。最终 B0/B1 完整 biome check . 均退出 0。
- TypeCheck: pass。最终 B0/B1 的 tsc --noEmit 均退出 0。
- Tests: pass。B0 为 27 项，B1 为 41 项；8 份原测试逐字节保持，没有删除断言、提高超时或筛选测试。
- Build: pass。B0/B1 完整 tsc --noEmit && vite build 均退出 0。
- 已安装 .bin 命令与 package.json 完全一致；没有安装或升级依赖。六个正式门槛与冻结源码指纹一致，原 web/dist 不变。
- 独立原始数据复算：10,303 项检查、0 失败，覆盖 60 个主观测和 2 个完整流程。可见证据检查：138 项、0 失败。最终文档/CDP 检查：62 项、0 失败。
- 最终 task.py validate、git diff --check、cached diff check 均退出 0，暂存区为空。旧报告注入长度警告保留，各代理已补读全文。

| AC | 结论 | 主要证据（相对本任务） |
| --- | --- | --- |
| 1 | 通过 | evidence/scope/preflight.json；evidence/dispatch/dispatch.md；中文规划及两个 JSONL |
| 2 | 通过 | evidence/review/product-review.md；product-gates.json；numeric-review.json |
| 3 | 通过 | evidence/visible/recovery.json；fault-*-restore.json；evidence/review/visible-review.json |
| 4 | 通过 | evidence/gates/B0-*-1.json；B1-r1-*-1.json；evidence/implementation/gates/ |
| 5 | 通过 | evidence/visible/observations.json；observations.md；evidence/review/visible-review.json |
| 6 | 通过 | evidence/measurement/raw-r1/；journey-r1/；evidence/snapshots/experiment-r1.json |
| 7 | 通过 | evidence/review/numeric-review.json；final-documents.json；report.md |
| 8 | 通过 | evidence/dispatch/dispatch.md；本报告 |
| 9 | 通过 | evidence/review/scope-final.json；evidence/visible/cleanup.json；evidence/measurement/cleanup-r1.json |
| 10 | 通过 | evidence/scope/final-commands-2.json；evidence/review/final-documents.json；verification.md |

冷 /runs 资产正文从 2,419,860 降至 1,094,078 B，减少 54.79%；就绪中位数从 300.2 降至 234.0 ms。暖入口为 97.1→97.5 ms；首次使用中位数增加 20.1–33.6 ms。完整访问 transferSize 增加 16,333 B（0.66%）；逐文件离线 gzip 增加 19,453 B（2.50%）。原始高值保留，历史 225.0 ms 未作本轮结果或门槛。

CDP encodedDataLength 已直接从原始 network 请求累计：冷入口全部为 2,422,997 / 1,099,642 B，冷入口资产为 2,420,106 / 1,096,273 B，完整访问全部为 2,484,052 / 2,499,315 B。各值与 report.md 一致。URL 并集、实际传输、离线 gzip、原生 FCP 和页面就绪分别报告。

29 条可见 DOM 记录覆盖 390/1280 px 全部要求。17 张 inline 图片没有保存为文件。两次真实缺块恢复覆盖空/非空 hash，恢复后页面和预测 Canvas 正常。旧评估 463 个文件、原 dist、launch 与 34 个夹具的 SHA-256/大小/mtime 保持。12 次性能服务测量退出 0，主动中断后的服务退出 3；故障资产还原，9000 释放，视口恢复，自有标签关闭。

最终 B1 源码版本为 9da4838b462bfc8cd5181ebd5c7cc0bffe43122c72ac8cd9b5c933b95201f07a，产物版本为 a27404802c27827e1f4c2955517400f8fd4e56b77cd8862f93d6c0fad8b937a7。当前 5 个产品文件与 2 份 specs 均已核对。8 个冻结规划/报告/派发文档的完整 SHA-256、审查脚本版本、原始 CDP 文件哈希及检查结果保存在 evidence/review/final-documents.json，并与 evidence/scope/final-commands-2.json 一致。

本报告完成后不再修改冻结文档或执行重复验收。后续 Git 收尾须由用户另行授权。
