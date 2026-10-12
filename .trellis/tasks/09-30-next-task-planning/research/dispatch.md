# 规划代理派发与所有权

日期：2026-09-30。任务状态：planning。派发前主会话实际执行 task.py current，返回 .trellis/tasks/09-30-next-task-planning。HEAD 为 945a76ecf35303083aec36acd5e879a3aa409aba。

## 用户授权

用户明确批准仅设置本会话活动任务指针。未授权产品实施、task.py start、任何测试/构建/服务/性能实验、安装、真实数据操作或 Git 写入。此前指针冲突已解决；本文件不扩展批准范围。

## 已派发角色

| 代理 | 真实工具角色 | 所有权 | 工作 |
| --- | --- | --- | --- |
| /root/product_research | trellis-research | research/current-state-candidates.md；必要时 research/research-source-index.json | 当前产品、指定报告、至多三个候选及最小验收建议 |
| /root/independent_review | default，明确只读规划审查职责 | research/independent-evidence-review.md、research/independent-candidate-review.md；后续 research/independent-final-review.md | 独立核对事实、契约、依据与验收机制，禁止自动修复产品或规划 |
| 主会话 | 协调 | task.json、三份规划、清单、验收映射、其他本任务研究文件 | 用户决策、证据综合、方案写作、范围验证 |

两个派发首行均为 Active task: .trellis/tasks/09-30-next-task-planning。均声明共享工作区、不撤销其他作者改动、禁止递归派发。两者 fork_turns=none，未指定模型或推理覆盖；不借主会话完整历史替代上下文核对。

## 上下文与方法

- 原生 SubagentStart 优先；截断时补读明确的完整输出。缺失时研究代理读取 research.jsonl，独立审查读取 check.jsonl，再按 prd→已存在design→已存在implement 补读。
- 专门的 research.jsonl 遵守研究角色对 implement/check 清单的隔离要求，同时落实用户的 jsonl→prd→design→implement 回退顺序。
- 两者均被要求补读八份指定报告全文和 B1 closure 说明/回执；不得仅依赖 archive-evidence.md。旧报告 37,508 字节超过单文件注入上限，需分段读取。
- 独立审查使用 trellis-plan-review 的事实/推论和逐条验收机制审查方法。用户规定的写入范围优先，报告仅写本任务 research/，不调用会写 .trellis/reviews/ 的 helper。
- 真实上下文注入是否发生、补读方式与完成范围，由各代理在其报告中记录。本文件不预先声称 hook 已运行。

## 迭代控制

当前现状与候选研究已完成；证据预审没有未解决发现。沿用同一独立审查代理复核两个候选，只核对新增相关事实、范围、验收建议和用户决定；返修轮次为 0/3。尚未开始完整方案终审。候选或验收发现回灌同一研究代理及同一任务；仅复核受影响内容，最终对收敛的完整方案独立审查。需要产品/范围/风险决定时，由主会话提出一个最高价值问题并等待。

方向尚未确认时，不将 design.md、implement.md 尚未创建当作初步研究的虚构缺陷；但不得将不完整材料标记为最终可批准方案。

## 方向确认后的完整方案审查

用户 D3 已选择说明一致化并保持运行行为；主会话编写三份方案及验收映射。第一轮（1/3）仅修订候选报告的必要生成物、合法保存与分类前提表述。独立代理继续复核这些受影响内容并对完整方案终审，报告写 research/independent-final-review.md。没有派发实施或新增任务。
