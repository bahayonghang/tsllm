# 研究：只读规划的派发前置核对

- 日期：2026-09-30。
- 范围：本地仓库只读核对，仅本任务材料可写。
- 查询：真实 task.py 创建与派发协议能否满足唯一写入根目录。
- 状态：需要用户决定范围冲突，尚未完成产品现状研究。

## 事实与来源

| 事实 | 可核实位置 |
| --- | --- |
| create 创建 planning task.json、prd.md、两个空清单。 | .trellis/scripts/common/task_store.py:528-590 |
| create 未带 --no-start 时调用 set_active_task，持久化本会话指针。 | .trellis/scripts/common/task_store.py:626-678 |
| 活动任务目录固定为 .trellis/.runtime/sessions/。 | .trellis/scripts/common/active_task.py:253-254 |
| set_active_task 写回 current_task 会话元数据，不修改任务 status。 | .trellis/scripts/common/active_task.py:732-763 |
| current 不从 planning 任务列表推断活动任务。 | .trellis/scripts/task.py:296-335；.trellis/scripts/common/active_task.py:646-678 |
| 所有代理派发首行要求 task.py current 返回的实际任务路径。 | .trellis/workflow.md:234、240 |
| Codex 原生 SubagentStart 注入优先，缺失时由子代理补读。 | .trellis/config.yaml:111-130；.codex/hooks.json:14-24 |
| research 角色只写 research/，配置要求角色隔离，不默认加载 implement/check 清单；check 缺失注入时加载 check.jsonl 后读取规划文件。 | .codex/agents/trellis-research.toml:15-33、49-60；.codex/agents/trellis-check.toml:18-25 |

用户本轮明确要求派发回退按存在的 jsonl→prd→design→implement 顺序。后续派发将显式传递该用户要求，说明角色配置差异，仅加载相关规划上下文；注入内容不得扩大写入、实施或测试授权。

## 已执行与观察

1. HEAD 为 945a76ecf35303083aec36acd5e879a3aa409aba，分支为 codex/frontend-route-lazy-loading。
2. 创建前 git status --short --untracked-files=all 无输出；完整 status 为干净。
3. task.py list 显示 0 个活动任务；现存 task.json 中没有同名或同目的任务。
4. 按已有创建授权，执行带非空标题与描述的 task.py create ... --slug next-task-planning --no-start。实际返回 .trellis/tasks/09-30-next-task-planning。
5. 创建后 task.py current --json 返回 current_task: null、source: none、stale: false。工具提示不构成运行 task.py start 的授权。
6. 未设置会话指针，未派发代理，未改产品，未运行测试、构建、服务或性能测量。

## 冲突与建议

用户限定的唯一写入根目录不包含 .trellis/.runtime/sessions/。真实派发协议又依赖该目录中的会话指针。当前解析器不从未激活的 planning 任务目录推断活动任务。

建议申请一个精确例外：允许 Trellis 现有 set_active_task API 设置本会话指针，目标仅为本规划任务；不调用 task.py start，不改变 status，不写其他会话指针或日志。此建议尚未获准。

若获准，先核对 HEAD、完整 status、任务内容和本会话 identity；使用现有 API 设置指针，再用 task.py current --json 验证实际路径和 planning 状态。派发使用返回路径，不伪造 current 输出。

若不获准，等待用户决定调整活动路径要求或多代理要求，不自行改用虚构路径、历史任务或其他会话。

## 尚未取得的证据

部分指定报告输出超过工具上限，现有阅读不满足完整证据要求。后续必须分段补读全文，包括 37,508 字节的 frontend-load-assessment/report.md（超过默认单文件注入上限 32,768 字节）。

尚未形成候选比较、推荐方向、验收设计或独立审查结论。未运行的未来门槛不得记为通过。

## 暂停时的材料检查

task.py validate 已通过两个清单各 1 条真实 research 引用。第一次新增文件空白检查发现 create 产物存在 CRLF 转换警告及 task.json 缺少末尾换行，已仅在本任务目录内统一为 LF 并补齐末尾换行。Git 变更为本任务的 5 个文件，范围外变更为 0。产品测试、构建、服务、性能实验与独立规划审查均未运行。

## 用户决定与恢复（2026-09-30）

用户明确答复：允许这一项指针写入（推荐）；继续研究和独立审查代理。随后只调用现有 set_active_task 设置本会话指针，task.py current 实际返回 .trellis/tasks/09-30-next-task-planning；source 为 session:codex_01a0f268-1a65-7633-9654-8b6b4fe2d0a8，status 仍为 planning。未运行 task.py start。此前暂停结论保留为历史记录，当前已解除该项阻塞。指定报告的分段全文补读已完成，见 archive-evidence.md。
