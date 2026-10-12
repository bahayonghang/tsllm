# 实施步骤规划

2026-09-30；planning。以下步骤均为未来计划。用户选择方向不等于实施批准；本轮不执行产品生成/测试/构建/服务，不运行 task.py start，不派发产品实施。

## S0：实施前重新核对

最终摘要之后取得明确实施批准，才核对当前任务实际路径、HEAD/分支/完整 status、适用规则和最新独立审查。参考起点 945a76ecf35303083aec36acd5e879a3aa409aba；HEAD 变化时评估十文件和契约影响，不回退或切历史分支。范围外脏文件保留，写入冲突时停止。

保存十文件基线、保护产物/冻结源哈希；确认新测试未被他人创建。只用已安装离线环境，不 sync/add/install。原生注入优先，缺失时读对应 jsonl→prd→design→implement；清单先 task.py validate。未来子代理明确所有权，不递归派发、不新建任务树。

## S1：受限契约说明

按 M1 修改两个现有规范文件，英文角色矩阵与用户 D3 对应；两个 index 入口及原数据契约引用明确限定优先级。冻结父/子原件保持，其余契约不变。未来验收前不新增 Verified 声明。

## S2：源描述及生成同步

仅改 ChannelSpec.role.description，运行 G1/G2 后审查预期差异；相同版本再生成，比较两次字节。单独核对 enum/default/类型/API 形状、实例序列化和哈希不变。生成无关漂移时停止，不手工删漂移、不升级依赖，不改 RunConfig 夹具。

## S3：页面说明

按 M2 在通道卡片 Table 前放静态中文提示，四个状态均显示；不改角色、保存能力、执行校验、错误映射或路由。既有 stale 提示保留，不自动入库或提交。

## S4：合成回归

按 M4 添加两个测试文件并补充两个既有服务测试文件。覆盖三拒绝组合、分类 past 的校验前提及真实 _embed 上下文、四角色合法保存、非法保存不落盘、schema 和中文说明。仅临时合成数据，不调用真实模型/训练，不改变原断言。

## S5：正式门槛与可见验收

以下命令来自当前真实来源，本轮全部未运行。两项生成步骤与七个质量门槛分别记录。

| 编号 | 根目录命令 | 来源 |
| --- | --- | --- |
| G1 | uv run tsllm api openapi --out web/openapi.json | .trellis/spec/frontend/api-client.md:9；src/tsllm/cli.py:230-239 |
| G2 | pnpm -C web run gen:api | web/package.json:12；.trellis/spec/frontend/api-client.md:10-11 |
| G3 | uv run ruff check | .trellis/spec/backend/quality-guidelines.md:14 |
| G4 | uv run ruff format --check | 同上 |
| G5 | uv run pyright | .trellis/spec/backend/quality-guidelines.md:15 |
| G6 | uv run pytest | .trellis/spec/backend/quality-guidelines.md:16-25；pyproject.toml:59-65 |
| G7 | pnpm -C web run check | web/package.json:9：biome check . && tsc --noEmit |
| G8 | pnpm -C web run test | web/package.json:11：vitest run |
| G9 | pnpm -C web run build | web/package.json:8：tsc --noEmit && vite build |

未来只对命令进程设置 UV_OFFLINE=1、UV_NO_SYNC=1 防止安装/下载，先核实工具已安装。pnpm 若要求 bootstrap 下载则停止；可用已安装 .bin launcher 执行完全相同脚本，记录 cwd/参数/哈希/退出码，不能省略 tsc/Biome/完整测试。该方式的既有记录是归档 B1 .trellis/tasks/archive/2026-09/09-30-frontend-route-lazy-loading/verification.md:39-49，不作为本次运行结果。

G7–G9 在最终批准源和配置/锁文件的隔离副本内执行，保持 web/ 结构与原脚本参数；依赖引用已有安装。只复制必要版本化文件和获批差异，禁整仓/私有数据/备份复制；原 web/dist 不变。G1/G2 的预期生成变更在未来获批产品工作区审查，本轮不生成。

可见验收按 M5：同修订生产构建、隔离 Settings/合成夹具、环回可见 in-app browser、1280/390 px。V1 文案、V2 保存/取消、V3 无文档溢出、V4 新鲜合成 Canvas、V5 身份/路径隔离均须通过。只用 GET 与通道 PUT，禁止入库和运行提交。设置 web_dist 必须显式传给临时 app factory，不能猜环境变量。截图只会话内。jsdom 不能替代可见门槛；不能因环境缺失而使用真实数据。

不做新性能/CUDA/真实数据验收。路由机制不变时，原恢复单测仍通过完整 G8；历史真实缺块恢复只标记复用。触及路由边界先回规划，不自动扩展。

## S6：独立验收、首败与回滚

独立代理将完整 diff 对 N1–N7/P1–P7 核对，验证机制和证据来源。每次尝试保留修订身份、原输出和真实退出码；首败和修正复测分别编号，同修订复测，不放宽任何断言/阈值/timeout。最多三轮同任务返修，只复核受影响项，最后完整审查。

按 M6 的十文件基线和所有权回滚；源 schema/生成物、规范例外/UI 成对撤回。保护 B1、他人修改、冻结证据与 D3，禁止 reset/clean 或 HEAD 回退。回滚后比较完整 status 和保护哈希。产品回滚也须届时授权。

## S7：本轮规划收尾

当前只执行 task.py validate、本任务 UTF-8/换行/尾空白、git diff --check、完整 status 和路径/哈希检查。主会话记录完整独立终审和逐项规划验收，展示最终摘要后停止。G1–G9、V1–V5、回滚操作和全部产品门槛均保持未运行；不提交、归档或实施。
