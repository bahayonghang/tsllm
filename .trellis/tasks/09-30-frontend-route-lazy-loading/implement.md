# 实施与验收顺序

1. [x] 核对授权、Git 基线/分支/status、无产品 diff、嵌套规则、共享契约、旧 recovery-r1 与派发协议。
2. [x] 持久化受保护快照、中文规划与真实 JSONL；task.py validate 后正式 start。
3. [x] 派发 trellis-implement：仅三类产品源文件及对应测试；记录上下文注入/回退与完整变更；保留原测试。
4. [x] 并行派发任务工具代理：从可追溯材料准备隔离快照、夹具、正式门槛与版本绑定采集器；不先占用端口。
5. [x] 独立 trellis-check 初检产品、测试、范围；无产品 findings，尚未使用聚焦返修轮次。
6. [x] 冻结最终产品快照；核对 package scripts；完整 check/test/build，保留首次失败与每次退出码。
7. [x] 使用同一最终 dist：主会话可见验收双视口、深链接/历史/表单预览/Canvas/警告/空值/禁选；真实缺块并还原后点击恢复，证实文档 reload 和地址保持。
8. [x] 同期交替 2×6×5 主矩阵、两次完整流程；新空目录与 sidecar；保留原始/失败/高值；独立复算与收益判断。
9. [x] trellis-update-spec 同步直接受影响 frontend 契约及过时单块描述；verification/report 逐条对齐 AC。
10. [x] 最终全范围独立 trellis-check；完整性、清理、task.py validate、git diff --check 与范围核对。明确未暂存、提交或归档。

## 正式命令

`pnpm -C web run check` = `biome check . && tsc --noEmit`；`test` = `vitest run`；`build` = `tsc --noEmit && vite build`。核对源为 web/package.json。旧评估已验证 pnpm 12 自动安装准备问题，允许在隔离副本直接调用已安装 node_modules/.bin 的完全相同子命令；记录实际 launcher、版本及输出。不得安装/升级、改构建配置、超时或断言。

## AC 与证据映射

| AC | 机制/检查 | 计划证据 | 所有者 |
| --- | --- | --- | --- |
| 1 | 完整 Git/保护快照、manifest 校验、正式 start | evidence/scope/preflight.json、git-status-before.txt、dispatch/ | 主会话 |
| 2 | 七路由/重定向/地址测试，入口资源集合 | 产品测试、gates/、measurement/ | 实施+采集+checker |
| 3 | deferred/rejected import 测试、真实点击恢复 | 产品测试、visible/recovery.json | 实施+主会话 |
| 4 | 原脚本完整门槛，源码/产物指纹 | gates/、snapshots/ | 实施+工具 |
| 5 | 双视口真实控件/Canvas | visible/observations.json、visible/observations.md | 主会话 |
| 6 | 交替矩阵、全流程、版本 sidecar | measurement/raw-r1/、journey-r1/、snapshots/experiment-r1.json | 工具+主会话 |
| 7 | 原始数据独立数值/HTTP/gzip复算 | review/numeric-review.json、report.md | checker+主会话 |
| 8 | 实际派发、最多三轮、最终全范围 | dispatch/、review/ | 主会话+checker |
| 9 | 哈希/大小/mtime、PID/端口、故障/浏览器清理 | scope/final.json、visible/cleanup.json | 主会话+checker |
| 10 | 逐项记录、spec同步、任务/diff校验 | verification.md、review/final.md | 主会话+checker |

## 权限记录

本轮 Prompt 同时明确授权任务创建、规划、start、实施及验收；不再次请求同一授权。Git 收尾没有授权。只在实质范围/共享契约冲突或其他指定暂停条件出现时停止受影响工作。
