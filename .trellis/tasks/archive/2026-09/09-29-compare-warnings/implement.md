# 实施计划

## 0. 阶段与开始条件

- [x] 用户选择 A+B，确认保留结果、增加警告。
- [x] 2026-09-29 创建独立 P2 规划任务，使用 --no-start，创建时未激活。
- [x] 规划文件和上下文清单完成校验。
- [x] 2026-09-30 用户在最新规划摘要后明确批准实施。
- [x] 实施前复核 main/7829f557，仅有本任务规划文件，没有其他工作区改动。
- [x] 已核查并创建 codex/compare-warnings，HEAD 保持 7829f557，未覆盖其他分支。
- [x] 已读取 trellis-before-dev 并向实施代理提供规范清单；task.py start 已成功，状态为 in_progress。

实施阶段授权覆盖已确认范围的实施及验证。2026-09-30 用户另行授权本地工作提交、归档、引用修正和日志；其他 Git 及发布操作仍未授权。

## 1. 接口与比较

1. 增加合成接口用例，先记录当前遗漏的失败证据。入库夹具不写 metrics.json。
2. 覆盖同数据集且均成功的混合、反序、单入库、全入库、重复 ID、未成功入库及其他既有差异。
3. 比较模块按 JobSpec.kind 增加警告，保持列、指标及原判定。
4. 为状态及起点警告增加 run_id/split，响应字段可选，保留原 code/message。
5. 检查合成文件和状态不变，覆盖 404、422、去重及正常实验回归。

## 2. 类型与页面

1. CLI 生成 OpenAPI，再生成前端类型；差异仅含批准扩展。
2. 局部中文映射使用服务上下文及运行列，不解析英文句子。
3. 保留旧响应、未知码、缺少关联列及同码多条，保持空值和选择规则。
4. 页面测试改用英文真实响应形状，覆盖中文及手工混合链接；按需增加格式化和列表选择测试。
5. 两次生成 OpenAPI/TypeScript，比较字节或 SHA-256。首次预期扩展不以旧 HEAD 零差异作为通过条件。

## 3. 环境与验证命令

使用预装依赖，每组 uv 前检查其他 uv sync，存在时等待，不终止无关进程：

~~~powershell
Get-CimInstance Win32_Process -Filter "Name = 'uv.exe'" |
    Select-Object ProcessId, CommandLine
~~~

测试进程设置 HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1、UV_OFFLINE=1、UV_PYTHON_DOWNLOADS=never。隔离缓存和代理沿用批准的进程级离线口径，并记录实际设置。环境变量仅作用于验证进程；不改网络、防火墙或全局配置，不设置空 CUDA_VISIBLE_DEVICES。依赖不足时报告，不自动联网下载。

以下为实施验证命令；实际执行结果写入 verification.md，不以本清单代替执行证据：

~~~powershell
# 针对性检查；新增局部用例也需纳入
uv run pytest tests/service/test_api_compare.py
uv run tsllm api openapi --out web/openapi.json
pnpm -C web run gen:api
pnpm -C web exec vitest run tests/pages/ComparePage.test.tsx

# 后端正式门槛
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest

# 前端正式门槛
pnpm -C web run check
pnpm -C web run test
pnpm -C web run build

# 差异及私有目录检查
git diff --check
git ls-files -- data ref runs cache
git status --short
~~~

默认 pytest 的合成/微型模型检查属于正式门槛。本任务不运行真实实验、GPU/weights 验收或父任务整套集成流程。既有体积警告单独记录，不提高阈值或扩大范围。

## 4. 可见浏览器

1. 独立临时目录准备合成 configs/cache/runs，仅含终态作业，覆盖正常、未成功、划分差异、入库及混合场景。
2. 给服务设置 TSLLM_RUNS_DIR、TSLLM_CACHE_DIR、TSLLM_CONFIGS_DIR，均指向临时子目录。核对目录及 9000 可用，不终止无关进程。
3. 生产构建由以下服务托管，不走仍指向 8000 的 Vite 代理：

~~~powershell
uv run tsllm serve --port 9000
~~~

4. 可见窗口检查 390 px、1280 px 的提示、上下文、选择限制、手工链接、空指标和正常无警告场景。
5. 截图仅留会话。记录服务身份，仅停止本任务启动的服务。

## 5. 验收映射与检查

| AC | 必须取得的证据 |
| --- | --- |
| AC1 | 七类中文提示及多运行/划分上下文的页面和浏览器证据 |
| AC2 | 接口组合矩阵、200、每个去重入库一条新警告 |
| AC3 | 指标/顺序、null/空行、合成文件和状态前后对照 |
| AC4 | 正常无警告、去重、404、422 |
| AC5 | 旧响应、未知码、缺少上下文、同码多条 |
| AC6 | 选择限制、手工链接、两种宽度的可见浏览器 |
| AC7 | 旧消息、可选字段、连续生成哈希及差异 |
| AC8 | 正式门槛、差异范围、私有内容检查、未执行项 |

实施与检查按项目 auto 模式使用 Trellis implement/check 代理，优先原生上下文注入，缺失时由子代理读取。

仅在本任务需要规则时更新对应规范，不顺带修复历史文档、构建或其他 API。证据写于本任务目录，区分通过、失败后复验和未执行。

## 6. 回退与交付

- 未提交时只撤回本任务改动，保留他人修改，不 reset/clean 或批量恢复。
- 已有独立提交时 Git 回退另需授权；代码/schema/type 一起恢复并重建前端。
- 不修改或恢复私有目录，不删除备份或迁移历史运行。
- 实施后交付质量结果及差异。后续本地收尾按 2026-09-30 的单独授权执行；不推送、不合并、不创建 PR、不发布、不删除分支。

## 7. 实际完成状态（2026-09-30）

- [x] 接口回归先失败后通过；kind 识别、追加警告、上下文及只读性验证完成。
- [x] 页面七码中文提示、英文响应夹具、旧响应及未知码降级、重复提示与入口回归完成。
- [x] OpenAPI/TypeScript 连续两轮官方生成与 LF 规范化，最终字节及 SHA-256 一致。
- [x] 后端四门槛、前端三门槛通过；默认 pytest 为 180 passed、5 deselected、3 warnings。
- [x] 独立 trellis-check 全范围检查通过，无修复和新增阻断项。
- [x] 9000 隔离服务、实际 HTTP 六组合、可见 IAB 390/1280 px 与两种入口验收完成。
- [x] 服务正常关闭，9000 无监听；浏览器视口恢复，临时标签关闭。
- [x] 按 trellis-update-spec 更新后端警告契约及前端展示规则；完整证据见 verification.md。
- [x] 用户另行授权本地收尾；产品及规范 10 个文件与独立验收哈希一致。
- [x] 工作提交 1060a432e384b96d326ce4e5530809b17ef4532d 已包含本任务 18 个路径；正式归档命令完成，8 份任务材料已移动，三处引用已修正。归档改动单独提交。
- 日志阶段按顺序在归档提交后执行。最终记录位于 .trellis/workspace/lyh/journal-1.md 的“对比警告本地收尾与归档”会话，引用上述工作提交。
