# 父任务执行计划

父任务不直接写产品代码。本文件规定子任务顺序、每个阶段的门禁和最终集成审查。

## 顺序

| 顺序 | 任务                      | 开始条件                                                  | 完成条件                                                        |
| ---- | ------------------------- | --------------------------------------------------------- | --------------------------------------------------------------- |
| 0    | `00-bootstrap-guidelines` | 无                                                        | `.trellis/spec/` 无占位文字；`AGENTS.md` 含项目说明；提交并归档 |
| 1    | `09-28-data-contract`     | 0 已归档                                                  | 子任务验收全部勾选；提交并归档                                  |
| 2    | `09-28-backbone-adapters` | 1 已归档（依赖 `ContextBatch`、`SegmentSet`、`FitStats`） | 同上                                                            |
| 3    | `09-28-experiment-runner` | 1、2 已归档                                               | 同上；AC3、AC4 的 CLI 部分完成                                  |
| 4    | `09-28-service-api`       | 3 已归档                                                  | 同上                                                            |
| 5    | `09-28-web-ui`            | 4 已归档（依赖 OpenAPI）                                  | 同上；AC5、AC6 完成                                             |
| 6    | 父任务集成审查            | 1–5 已归档                                                | 跨子任务验收 AC1–AC7 全部勾选                                   |

每个子任务独立执行 `task.py start` → 实施 → `trellis-check` → 规范更新 → 提交 → 归档。一次只处理一个子任务。

## 契约变更规则

子任务实施中发现 `design.md` 的共享契约不可行时：

1. 停止实施，回到本父任务修改 `design.md` 对应小节。
2. 检查已归档子任务是否受影响；受影响时在当前子任务的 `implement.md` 中加入修复步骤。
3. 在当前子任务 `prd.md` 的备注中写明契约变更。

## 统一验证命令

```bash
uv sync
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest
```

前端（web-ui 子任务起）：

```bash
pnpm -C web install
pnpm -C web run check
pnpm -C web run test
pnpm -C web run build
```

需要 GPU 或权重的测试用 pytest 标记 `gpu`、`weights`，默认不运行：

```bash
uv run pytest -m "gpu or weights"
```

## 权重准备（AC3、AC4 前）

权重下载需要网络。可选方式：

- 设置 `HF_ENDPOINT=https://hf-mirror.com` 后由适配器首次加载时下载。
- 预先下载到本地目录，在 RunConfig 的 `backbone.checkpoint` 写本地路径。

需要的检查点：`amazon/chronos-2`、`google/timesfm-2.5-200m-transformers`、`ibm-granite/granite-timeseries-ttm-r2`。revision 在首次成功运行后写入 `configs/runs/` 下的样例配置。

## 集成审查清单（顺序 6）

- [x] 在干净克隆上执行统一验证命令，全部通过。
- [x] 按 AC2 执行水泥数据入库，记录行数、段数、各划分时间边界。
- [x] 按 AC3、AC4 执行运行，结果目录路径写入父任务 `prd.md` 备注。
- [x] 按 AC5、AC6 在网页中操作一遍，记录操作步骤与截图位置。
- [x] 检查 `runs/`、`cache/`、`data/`、`ref/` 均未入库。

2026-09-29 集成审查：按用户要求复用 fresh 缓存及九项成功历史运行，完成两个 ETTh1 网页提交和可见画布检查。默认 Windows 克隆的前端格式检查有 44 项 CRLF 错误；`.gitattributes` 固定 LF 后模拟检出通过。对比柱状图改为底部图例，浏览器复核无重叠。两项修复提交为 `4b46719`；提交 `63d747d` 的默认 Windows 干净克隆统一验证全部通过，统一验证项已勾选。证据、偏差与遗留问题见父 `prd.md` 的备注。

2026-09-29 收尾：用户批准将 AC1 调整为预装依赖、空模型缓存、进程级离线设置下的默认测试通过且不下载权重。当前 HEAD `ee96495` 的干净克隆执行 `uv run pytest`，165 passed、5 deselected、3 warnings，退出码 0；模型缓存前后均为 0 个文件。AC1–AC7 全部勾选。整机断网环境未验证，证据边界和规范更新检查见父 `prd.md`。

## 回滚

每个子任务单独提交。某子任务验收失败时，只回退该子任务的提交；已归档的前序子任务不回退。
