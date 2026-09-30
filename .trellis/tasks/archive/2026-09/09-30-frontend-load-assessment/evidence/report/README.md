# 报告复算说明

本目录只承担 report.md 的数值生成。脚本读取保留的 Navigation/Resource Timing 原始记录，重新构造 URL 集合与各时间窗口，独立计算中位数、最小/最大、字节差和百分比。脚本不导入测量汇总实现，不访问私有目录，不启动服务或浏览器。

## 原始修订

`original-report.md` 与 `original-recomputed.json` 保存原始 90 个主观测和 3 个补充旅程的报告快照。保存时已知 B1 实际同 URL 链接恢复失败，所以该快照不代表完整验收通过。原始数据仍保留在 `../measurement/raw/` 和 `../measurement/journey/`。快照的 build 清单与 raw/summary SHA-256 用于绑定旧修订证据，不随修复重测覆盖。

原始报告生成曾断言每个冷/热文档存在 FCP。复算发现 B0 的 10 个目标快照均无 FCP，断言失败。脚本已改为保留缺失，并显示采集数 0/5；不插补，不将缺失值转为 0，不改测量脚本。首次脚本 lint 另发现行长和未使用局部变量，已修正。

后续独立调查确认原始 FCP 缺失由 paint 条目晚于就绪快照发布引起，浏览器支持 paint API。主会话另行修订收集器并重新执行完整矩阵。上述 0/5 属于原始修订的历史证据，不能表述为恢复修订仍缺失或浏览器不支持。

## 修复后修订

从仓库根执行：

```powershell
python .trellis/tasks/09-30-frontend-load-assessment/evidence/report/recompute_report.py --measurement-root .trellis/tasks/09-30-frontend-load-assessment/evidence/measurement/recovery-r1 --variant-root .trellis/tasks/09-30-frontend-load-assessment/evidence/variants --revision recovery-r1
```

输入目录必须同时包含 `raw/`、`journey/`、`summary.json` 和 `journey-summary.json`。资产必须与同修订 inventory 一致。脚本要求每个主组合恰好 5 个有效观测、每个旅程恰好 1 个，不跨修订合并；任何输入不一致直接停止。`--report` 和 `--output` 可显式指定报告和复算结果路径。

生成器只替换 report.md 的 `generated-results` 区域和 `recomputed.json`。修订状态、决策说明、门槛、可见验收及 AC 状态须由报告归属代理依据新证据更新，不能仅运行生成器便宣称报告完成。

## 验证

原始与恢复修订分别完成 93 个观测、21 组的重新计算，每个修订均通过 2,277 个汇总统计数值核对。当前 `recomputed.json` 对应 recovery-r1，历史结果保存在 original-recomputed.json。Ruff check、Ruff format --check 与单文件 Pyright 在生成器上次修改后通过，本次仅替换输入修订，未重复运行产品构建或测试。

生成器保留全部 URL、样本值、输入文件哈希和自身哈希；存在 FCP 缺失时不计算涉及缺失基准的差值。恢复修订冷/热六组目标文档 FCP 全为 5/5。完整 paint 覆盖由 `../review/recovery-r1-paint-review.json` 独立复核，不把同文档重复阶段快照当作独立 FCP 样本。

正式产品门槛由方案证据承担。本目录验证不替代修复方案的正式门槛、重测、可见行为或最终范围核对。
