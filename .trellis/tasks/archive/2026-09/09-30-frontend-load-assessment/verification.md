# 前端加载评估验收

日期：2026-09-30（America/Chicago）。分支：`codex/frontend-load-assessment`。固定产品基线：`e9ce26a7bd1a4ed67cd30d257354e7345c44dec1`。验收修订：`recovery-r1`；测量工具修订：`paint-collection-r1`。

## 当前状态

评估实施与独立审阅完成，AC1–AC6 全部通过。最终结论只使用 recovery-r1 的 90 个主观测与 3 个补充旅程；原修订、首次失败和复测材料均保留。独立审阅确认报告与本文的事实、数字、分母、复现方法和行为复用范围一致，记录见 `evidence/review/continuation-review.md`。产品落地、提交及归档未授权，任务状态保持 in_progress。

## 验收追踪

| 条件 | 当前结论 | 对应证据 |
| --- | --- | --- |
| AC1 基线、产物、版本和 HTTP | 通过 | `evidence/variants/` 清单、依赖图、补丁及重现记录；`evidence/review/recovery-r1-variant-integrity.json`、`recovery-r1-http-review.json`。 |
| AC2 三方案 3×6×5 主矩阵 | 通过 | `evidence/measurement/recovery-r1/raw/` 和 `summary.json`：18 组各 5 个有效观测，共 90 个；0 个测量失败、0 次重试；三方案按轮次交替顺序。 |
| AC3 可复算资源与时间 | 通过 | `evidence/review/recovery-r1-numeric-review.json`：1,349 项统计/差值检查、1,755 条资产记录；`recovery-r1-journey-review.json`：302 项检查、489 条资产记录；均通过。 |
| AC4 正式门槛、可见行为和模块恢复 | 通过 | 三方案前端 check/test/build；`evidence/visible/observations.md`、`continuation.md`、`module-recovery-r1-route.json`、`module-recovery-r1-feature.json`。 |
| AC5 报告与建议 | 通过 | `report.md` 与 `evidence/report/recomputed.json` 已绑定 recovery-r1；2,277 项报告统计复算通过，93 个原始记录哈希一致；独立逐节审阅通过。 |
| AC6 独立检查、范围与清理 | 通过 | `evidence/review/recovery-r1-scope.json`、`evidence/visible/cleanup-after-matrix.json`、`evidence/review/continuation-review.md`；独立材料检查、task.py validate 与 git diff --check 通过。 |

## 两次缺陷与同条件复测

### 模块恢复

实际浏览器检查发现 B1 在含查询参数和片段的地址发生模块加载失败后，原恢复链接未触发文档重载。首次失败保留在 `evidence/visible/module-failure.json`，原失败未改写为通过。

修复仅发生在隔离临时 B1/B2：恢复操作阻止链接默认动作并调用 `globalThis.location.reload()`，保留 pathname、query 和 hash。修复前新增回归测试保留失败记录：B1 为 2 失败/37 通过，B2 为 4 失败/38 通过。修复后正式门槛通过。补丁、修复前后产物和逐文件重现记录保存在 `evidence/variants/recovery-r1/`。

实际浏览器重复缺块、显示错误、恢复同一 SHA-256 文件、点击恢复的流程。B1 路由与 B2 功能模块均恢复成功；查询参数及片段保持不变，错误提示消失，B2 结果图表恢复。所有临时缺块文件已还原。

### FCP 采集

原 B0 绘制数组缺失由采集时序导致：原生 paint 条目在就绪快照之后才发布。分析见 `evidence/review/paint-collection-analysis.json`。不能将该缺失解释为浏览器不支持 FCP。

修订采集器在原就绪条件之后等待原生 timeline/buffered observer，统一上限 1000 ms；保留 `paintAtReady` 和原 `start/end/duration/resources/navigation/longTasks`。额外等待不计入既有就绪指标。3 项语法检查、8 项确定性测试与 3 项 Biome lint 通过；lint 的信息提示和首次命令失败均保留。运行脚本哈希已冻结，每条观测与目录旁 instrumentation 清单均记录哈希。

B0 冷、暖缓存预检共 2 个观测、3 个文档阶段均取得原生 FCP。正式 93 个记录覆盖 108 个独立文档、213 个就绪快照：195 个 `stages` 快照及 18 个独立 `preview` 快照。213 个快照均为 observed；冷/暖缓存 FCP 六组各 5/5。33 个快照的 FCP 在就绪时尚未发布，补采后取得；1 个 FCP 原生时间确实晚于就绪终点，原值保留。额外收集等待范围为 0–6.8 ms。独立审阅见 `evidence/review/recovery-r1-paint-review.json`。

## 门槛与可见行为

| 方案 | check / test / build 最终记录 | 测试结果 |
| --- | --- | --- |
| B0 | `B0-check-4` / `B0-test-3` / `B0-build-4` | 35 项通过，原有 27 项保留。 |
| B1 | `B1-check-3` / `B1-test-4` / `B1-build-3` | 39 项通过。 |
| B2 | `B2-check-3` / `B2-test-4` / `B2-build-3` | 42 项通过。 |

门槛日志位于 `evidence/variant-gates/`。运行器使用已安装的 `.bin` 执行原 `package.json` 中相同命令，避开 pnpm 12 自动安装准备行为；未安装或升级依赖。原 B0 门槛因产品产物不变而复用；受恢复修复影响的 B1/B2 已重跑。新性能矩阵仍包含 B0。

390×844 与 1280×900 可见检查覆盖页面入口、深链接、查询参数、五个终态作业、入库行禁止勾选、三项实验选择、手工混合作业对比、七类警告、空值、表单模板和实际预览、数据集图表、预测图表、分类 ROC/PR 与混淆矩阵、系统页。B1 正常页面检查先于恢复补丁；恢复补丁仅改变错误恢复动作，正常行为证据按该范围复用，恢复行为另行同条件复测。B2 正常行为使用修复后的产物复核。

## 统计与解释边界

主矩阵每组 5 次，报告中位数和完整最小–最大范围。B2 第 3 次首次预测页观测为 2439.7 ms，有效样本未删除、未补采；原因未查明。三条完整旅程各方案仅 1 次，用于累计资源说明，不用于稳定耗时结论。旅程最终 ready_ms 只对应最后一次系统页导航。

测量使用本地环回、合成夹具、指定版本无头 Edge、1280×900 视口，无网络或 CPU 限速。冷缓存只指浏览器 HTTP 缓存；不声明操作系统、进程或代码缓存全冷。就绪指标包含统一观察器及两次稳定动画帧，不等同于 load、TTI 或真人可交互时间。长任务不能直接归因到特定包。gzip 为离线估算，实际 HTTP 传输单独记录。

## 范围与清理

独立范围检查确认：289 个基线跟踪文件哈希不变，暂存区为空，任务目录外新增未跟踪文件为 0，私有根目录跟踪文件为 0。产品、规范、锁文件、API 生成物、原 `web/dist` 与 `.claude/launch.json` 未变。`cache/datasets/ETTh1.acc-backup` 仅复核目录存在；未读取或遍历其内容作哈希比较。

本轮预检、主矩阵、补充旅程分别启动 1、15、3 个本任务服务实例，均已退出；9000 端口释放。34 个合成夹具文件的 SHA-256、大小、mtime 均不变，独立模型缓存为 0 文件，无遗留暂扣资产。可见浏览器视口已恢复、任务标签已关闭；之后未再使用可见浏览器或新增 inline 图片。证据见 `evidence/visible/cleanup-before-matrix.json`、`cleanup-after-matrix.json` 与各矩阵 lifecycle 文件。

未运行真实实验、训练、入库、权重下载或 GPU/weights 验收；未修改网络或防火墙。未变更构建阈值、minify、target 或依赖。未进行提交、归档、合并、推送、PR、发布或删除分支。后端实现未改变，因此未机械重跑后端四门槛。
