# Journal - lyh (Part 1)

> AI development session journal
> Started: 2026-09-28

---



## Session 1: Complete data contract and local validation
<!-- trellis-session: v=2 fp=218a9d76d1fad5d4 -->

**Date**: 2026-09-28
**Task**: Complete data contract and local validation
**Branch**: `codex/data-contract`

### Summary

Completed data-contract AC1-AC6 and archived the task. Preserved tracked Trellis workspace records and ignored generated diagnostic logs.

### Main Changes

- Implemented the data contract, synthetic regression tests, and data CLI; synchronized verified specifications.
- Retained historical baseline failure evidence and the user-approved AC4 reference correction.

### Git Commits

| Hash | Message |
|------|---------|
| `04bd695` | feat(data): 实现数据契约与数据集入库 |
| `05ba246` | chore: 完成数据契约收尾并忽略诊断日志 |

### Testing

- [OK] ruff check and format check passed; pyright reported no errors; pytest reported 87 passed.
- [OK] Local ingestion passed: yangquan_kiln 523782 eligible minutes, 43 segments, 4.535 s CLI and 6.763 s wall; ETTh1 17420 eligible points.

### Status

[OK] **Completed**

### Next Steps

- Begin 09-28-backbone-adapters in the next conversation. Other child tasks remain planned.


## Session 2: 基座适配层提交与归档
<!-- trellis-session: v=2 fp=8d1a5b46fd0a3d90 -->

**Date**: 2026-09-29
**Task**: 基座适配层提交与归档
**Branch**: `codex/backbone-adapters`

### Summary

完成 backbone-adapters 的六个适配器及 AC1–AC7。最终独立 trellis-check 通过：ruff check、ruff format --check、pyright 均退出 0，离线 pytest 125 passed、5 deselected、2 条库提示。三个真实检查点分别完成加载、零样本预测与 5 步微调；两项 LoRA 参数比例低于 5%；Chronos2 和 TimesFM25 的 CUDA bf16 预测通过；CUDA True，capability (12, 0)。保留 TTM 首次 freq_token 失败及同 revision 修正后的复测。保留 TimesFM quantile-loss 的已知库语义限制。Phase 3.3 只将已验证范围标为 Verified。按用户确认拆为依赖与功能两个本地提交，并通过 task.py archive 归档，归档提交为 9bd00fc。同步归档引用；父任务及 runner、service、web 仍保留，未开始后续实施，未推送。

### Git Commits

| Hash | Message |
|------|---------|
| `6f94aa2` | build(deps): 配置基座模型依赖与 CUDA 12.8 索引 |
| `c81d304` | feat(backbones): 实现六个适配器并完成本机验收 |

### Status

[OK] **Completed**


## Session 3: 实验运行器实现与本机验收
<!-- trellis-session: v=2 fp=429f55bb16ca5eb5 -->

**Date**: 2026-09-29
**Task**: 实验运行器实现与本机验收
**Branch**: `codex/experiment-runner`

### Summary

实现 RunConfig/JobSpec、预测与分类指标、RunStore 状态机、FileReporter、环境快照、worker 与 run/runs/schema 命令及 11 个样例配置；离线门禁全部通过（pytest 146 passed）；水泥 9 个运行经 CLI 全部成功，修复 CPU 峰值显存与 TTM revision 记录两处缺陷；Chronos-2 表示分类弱于统计特征，原因未查明。

### Git Commits

| Hash | Message |
|------|---------|
| `65b6f11` | feat(runner): 实现实验运行器并完成本机验收 |

### Status

[OK] **Completed**


## Session 4: service-api：FastAPI 服务与任务执行器
<!-- trellis-session: v=2 fp=e06f12f04f3b3361 -->

**Date**: 2026-09-29
**Task**: service-api：FastAPI 服务与任务执行器
**Branch**: `codex/service-api`

### Summary

实现 tsllm.service（REST、SSE、JobManager gpu/cpu 池、进程树取消、重启恢复、静态文件、serve 与 api openapi 命令）；状态表新增 queued→failed；AC1–AC8 满足，165 passed；本机 serve 提交水泥 persistence 运行并读取 SSE。

### Git Commits

| Hash | Message |
|------|---------|
| `212ccf2` | feat(service): 实现 FastAPI 服务与任务执行器并完成本机验收 |

### Status

[OK] **Completed**


## Session 5: web-ui：React 配置与结果展示网页
<!-- trellis-session: v=2 fp=2cb6fa9364b67c40 -->

**Date**: 2026-09-29
**Task**: web-ui：React 配置与结果展示网页
**Branch**: `codex/web-ui`

### Summary

实现 web/（Vite 8、React 19、antd 6、rjsf schema 表单、ECharts、TanStack Query、SSE 续读）；AC1–AC6 满足，20 项测试通过；内置浏览器完成配置、提交、监控、结果、对比与 ETTh1 入库；修复 SSE 回放重复请求、390 px 顶栏溢出、入库作业可选入对比。

### Git Commits

| Hash | Message |
|------|---------|
| `2b26ac4` | feat(web): 实现 React 配置与结果展示网页并完成浏览器验收 |

### Status

[OK] **Completed**


## Session 6: 平台父任务验收收尾与归档
<!-- trellis-session: v=2 fp=550901d285531ba7 -->

**Date**: 2026-09-29
**Task**: 平台父任务验收收尾与归档
**Branch**: `codex/web-ui`

### Summary

用户批准取消整机断网要求；当前 HEAD 干净克隆通过进程级离线默认测试，AC1–AC7 完成，父任务已归档。

### Main Changes

- 更新 AGENTS 状态、规范索引归档路径及 web 验收状态；保留已有 web-ui 事项。
- 归档九份父任务文件，同步现行父任务引用及上下文清单路径。

### Git Commits

| Hash | Message |
|------|---------|
| `322ff9258c501f7e24240dbfc86cbb83f7b49ff6` | docs: 完成父任务验收并同步规范索引 |

### Testing

- [OK] uv run pytest：165 passed、5 deselected、3 warnings，54.01 s，退出码 0；模型缓存前后 0 文件。
- [OK] 复用并核对 63d747d 九命令原始成功日志及 AC2–AC7 证据；全范围审查通过。
- [OK] 归档文件清单、七项验收、引用目标和 git diff --check 均通过；四个私有根目录无跟踪文件。

### Status

[OK] **Completed**

### Next Steps

- 推送 codex/web-ui 后，等待用户选择整体 PR 或按子任务分支分别合并；不启用 auto-merge。


## Session 7: 对比警告本地收尾与归档
<!-- trellis-session: v=2 fp=f3d4fd5d2bb34b8a -->

**Date**: 2026-09-30
**Task**: 对比警告本地收尾与归档
**Branch**: `codex/compare-warnings`

### Summary

按用户本轮授权完成 compare-warnings 的工作提交、任务归档及开发者日志。AC1–AC8 保持通过，产品与规范的验收哈希匹配，复用已有验证。

### Main Changes

- 工作提交包含 8 个产品/测试/生成文件、2 份规范和 8 份任务材料，合计 18 个明确路径。
- 正式 task.py archive --no-commit 将八份材料移至 .trellis/tasks/archive/2026-09/09-29-compare-warnings/，状态为 completed。修正后端规范及两份上下文清单引用，归档改动已独立提交。

### Git Commits

| Hash | Message |
|------|---------|
| `1060a432e384b96d326ce4e5530809b17ef4532d` | fix(compare): 补全对比警告并提供中文展示 |

### Testing

- [OK] 本轮核对 HEAD、main、本地 origin/main 与实际远端 main 的交接基线；暂存区起初为空，无额外改动，未出现远端任务分支。
- [OK] 10 项 SHA-256 与独立验收相同；复用后端四门槛（pytest 180 passed、5 deselected、3 warnings）、前端三门槛（27 passed）、独立检查、实际 HTTP 六组合、16 文件不变、390/1280 px 可见浏览器及双轮生成一致性证据。
- [OK] 本轮 git diff --check 与暂存差异检查通过，包含新增文件；task.py validate 的 11+10 条上下文通过；八份归档文件及目标路径完整，活动任务和本任务指针均为空。data/ref/runs/cache 的跟踪文件数为 0。
- [OK] 本轮未重跑应用门槛、启动服务或调用 uv；未执行真实实验、训练、入库、GPU/weights 验收、权重下载或整机断网。未处置 ETTh1.acc-backup，未修改 launch.json 或构建阈值。

### Status

[OK] **Completed**

### Next Steps

- 下一候选：前端加载影响与拆分收益评估。等待用户另行选择；未创建、激活或实施。未合并、推送、创建 PR、发布或删除分支。


## Session 8: 路由级延迟加载本地提交与归档
<!-- trellis-session: v=2 fp=68ccd9d1e5661e27 -->

**Date**: 2026-09-30
**Task**: 路由级延迟加载本地提交与归档
**Branch**: `codex/frontend-route-lazy-loading`

### Summary

用户另行授权后完成 B1 工作提交、独立自动归档、规范引用及证据收尾。旧加载评估任务保持未跟踪且未改动；未推送或发布。

### Main Changes

- 七路由 B1 实施与规划证据先进入历史，再以 4064878 独立归档。
- 补存11份原日志字节副本；任务级属性保留83份CRLF证据，冻结数据没有改写。

### Git Commits

| Hash | Message |
|------|---------|
| `934ba580e39a3ecee53abe936cc41ff5aaef0049` | perf(web): 实施路由级延迟加载并记录验收 |
| `15ebf629d9479eb7d03e23b8aca7f14e97d06607` | docs(web): 同步路由加载归档引用与收尾记录 |

### Testing

- [OK] 冻结产品与证据哈希一致；复用同修订完整 check/test/build、41 tests、可见验收、60主观测和2完整流程。
- [OK] 归档 validate、当前 diff --check、范围和历史对象核对通过；完整暂存原始证据空白检查退出2及限定通过结果均保留。

### Status

[OK] **Completed**

### Next Steps

- 待用户启动下一步 Prompt，对旧加载评估任务进行独立证据复核及本地收尾；不自动实施B2。
