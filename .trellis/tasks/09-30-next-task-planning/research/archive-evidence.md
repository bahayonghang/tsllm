# 指定归档材料的只读证据清单

日期：2026-09-30（America/Chicago）。记录者：主会话。状态：研究代理与独立审查的输入，不能替代独立结论。产品源码未修改，未运行产品门槛或新性能测量。

## 基线与来源

- 当前与参考 HEAD 均为 945a76ecf35303083aec36acd5e879a3aa409aba，分支 codex/frontend-route-lazy-loading。
- 主会话执行 git diff --name-only 934ba580e39a3ecee53abe936cc41ff5aaef0049 HEAD -- web src configs pyproject.toml uv.lock，输出为空。该检查证明这些路径的 Git 树与 B1 工作提交相同，不证明本轮重新通过运行时验收。
- 八份指定报告均已按行分段补读全文，未依赖截断的工具输出：父 prd.md 295 行、design.md 374 行；评估 report.md 394 行、verification.md 62 行、completion/closure-result.md 53 行、independent/final-review.md 87 行；B1 report.md 109 行、verification.md 96 行。
- B1 evidence/closure/README.md 41 行和 result.md 15 行已读全文。archive-receipt、postarchive-validation、precommit、log-preservation、receipt-launcher-failure、stage-byte-check-1、stage-whitespace-check-1 已解析。未重新执行历史核验器、构建、测量或浏览器验收。
- 前端与后端 spec index、web/package.json、pyproject.toml 已读取。仅读源文件，不安装、生成或运行门槛。

以下路径以仓库根目录为起点。P = .trellis/tasks/archive/2026-09/09-28-tsfm-platform；A = .trellis/tasks/archive/2026-09/09-30-frontend-load-assessment；B = .trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading。别名仅用于阅读，后续正式候选必须使用完整 path:line。

## 事实、判断边界与定位

| 编号 | 已确认的材料事实 | 来源与边界 |
| --- | --- | --- |
| F1 | 父平台包含数据、六适配器、预测/分类、文件运行记录、服务与网页，父任务 AC1–AC7 已完成。 | P/prd.md:22-107、111-131、266。为历史验收结论，本轮未读取真实运行或缓存。 |
| F2 | 整机网络隔离条件已由用户取消，验收限定进程级离线；不能把整机隔离未测直接改写为未完成任务。 | P/prd.md:111-117、243-258、290-295。 |
| F3 | 当前七条页面路由使用 lazy，布局同步，初始及导航加载状态存在；失败恢复保留 pathname/search/hash 并调用 reload。 | web/src/router.tsx:5-57；web/src/components/AppLayout.tsx:19-58；web/src/components/RouteLoading.tsx:5-38。源码事实，不是新可见验收。 |
| F4 | 旧评估 recovery-r1 包含 90 个主观测、3 个补充流程，支持 B1，不支持当前 B2；存在真实使用频率未知等限制。 | A/report.md:7-13、298-322、379-394。旧冷入口 225.0 ms 不作为当前性能。 |
| F5 | B1 正式实施使用另一组同期 60 个主观测和 2 个完整流程；冷入口历史中位数为 234.0 ms，首次访问增加 20.1–33.6 ms，暖入口无可辨别收益。 | B/report.md:7-19、23-34、91-99。不能和 A 的观测合并，也不能声称当前实测。 |
| F6 | B1 工作提交及归档已经完成，原报告中的未提交说明属于采集时点。 | B/evidence/closure/result.md:5-12；archive-receipt.json。工作提交 934ba580e39a3ecee53abe936cc41ff5aaef0049，归档 40648784376a5d3dc165e75f2aa981f9843722c4。 |
| F7 | 旧评估后续独立收尾也已完成，最后建议保留当前 B1。 | A/evidence/closure-20260930/completion/closure-result.md:9-19、23-31、43-53。工作提交 967644734806d9056af67fcc7c284d5147b9f97e，归档 60fc52f7b46b205181b2c83f697b3b2628bfca18。 |
| F8 | 两类历史首次失败及其修订结果保留，B1 暂存空白检查存在如实保留的退出 2，不能用旧评估后来的退出 0 覆盖。 | B/evidence/closure/README.md:18-41、result.md:11；A/evidence/closure-20260930/independent/final-review.md:37-67。 |
| F9 | 构建警告、离线 gzip、真实网络传输、功能就绪与 FCP 的含义不同。 | A/report.md:75-91、302、381-383；B/report.md:36-59、91-98。包大小或警告不能单独构成下一任务依据。 |
| F10 | 父 PRD 的旧遗留对比警告问题已有后续独立任务，不能从父文档末尾直接复用成新缺陷。 | P/prd.md:295；.trellis/tasks/archive/2026-09/09-29-compare-warnings/prd.md:77、95。后者记录 AC1–AC8 完成；代理应按需要再查当前实现。 |

## 共享契约待核对项

- P/prd.md:80-85 将过去与未来协变量列为不实现；P/design.md:89 写预测使用 target 与 past_covariate；src/tsllm/tasks/validation.py:22-26 明确拒绝预测中的 past_covariate。
- .trellis/spec/backend/index.md:54 将父 design 作为共享契约；error-handling.md:37、121 将 past_covariate 作为未实现示例。
- 这是可定位的文本/行为差异。历史决策和正确修订方向尚未完整核实，未据此断言应实现协变量、改写冻结文档或新建产品任务。需要研究与独立审查明确影响；如确属用户决策，则进入单问题等待。

## 冻结路径映射

权威已有映射：A/evidence/closure-20260930/preparation/reference-adapters/mapping.closure-v1.json。主会话只读核对四份适配件 SHA-256 均匹配，50 条目标全部存在：assessment implement/check 各 12 条，B1 implement/check 各 13 条。

- 旧评估根 .trellis/tasks/09-30-frontend-load-assessment 映射到 A。
- B1 冻结清单原件保持，加载使用 A 下 b1-implement.closure-v1.jsonl、b1-check.closure-v1.jsonl。每份 5 条旧评估引用已由映射覆盖。
- B1 自身旧根至归档根的映射由 B/evidence/closure/README.md:31-33、result.md:9 记录。
- 不批量改写旧报告、脚本、临时绝对路径、清单或冻结证据；不读取旧临时目录或私有数据。

## 现有命令源与未来验证边界

- web/package.json:6-12：check = biome check . && tsc --noEmit；test = vitest run；build = tsc --noEmit && vite build。
- AGENTS.md:31-34 列出后端 ruff check、ruff format --check、pyright、pytest，AGENTS.md:39-41 列出前端三门槛。pyproject.toml:59-65 的默认 pytest 排除 gpu/weights。
- 历史 B1 验证使用安装好的 .bin 包装器执行同一脚本，原因是 pnpm 自动准备风险；见 B/verification.md:39-49。该历史方法不自动批准本轮任何执行。
- 可见 Canvas、真实缺块恢复、query/hash 保持不能由 jsdom 替身替代；见 B/verification.md:69-78。未来若受影响，应在获准的合成隔离环境保留可见验收，失败原件与同修订复测分开记录。
- 未来具体命令、范围、回滚与门槛仍须按候选方向设计。此处只确认命令来源，没有运行测试、构建、服务或性能实验。

## 未完成与所有权

主会话负责本清单及 prd/design/implement/映射；研究代理负责 current-state-candidates.md；独立审查代理负责独立报告。共享工作区中不得撤销其他角色改动，禁止递归派发。当前没有最终候选选择或规划通过结论。
