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
