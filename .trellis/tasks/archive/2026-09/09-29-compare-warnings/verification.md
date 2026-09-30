# 对比警告验收记录

## 范围与基线

- 验证日期：2026-09-30。用户已确认实施 A+B，接口采用“保留结果、增加警告”。
- 分支：codex/compare-warnings；基线 HEAD：7829f557c1aac4d356a2a829b010eaa23de5ebed。实施前仅本任务规划目录未跟踪。
- 本任务保持独立，父任务及五个子任务的归档和既有 AC1–AC7 结论未变更。
- 实施验收阶段的授权不包含提交、推送、合并、发布或归档；后续本地收尾授权及复核见文末。

## 初始失败证据

实施代理先加入回归测试，再验证原实现：

- 命令：uv run pytest tests/service/test_api_compare.py。
- 结果：7 failed、7 passed、1 warning，1.93 s。
- 六个组合用例因缺少入库警告而失败；另一个上下文/顺序用例因旧实现缺少批准字段或警告而失败。失败来自业务断言，未发生导入、语法或环境准备失败。
- 临时日志：C:/Users/lyh/AppData/Local/Temp/tsllm-compare-implement-20260930-cf5d0288/backend-before.log。
- 页面初始回归：6 failed、1 passed，失败对应中文展示及兼容提示断言；记录于同目录 frontend-before.log。

## 验证环境

- 使用仓库已安装依赖，未执行依赖安装。每组 uv 命令前检查 uv sync；初次检查为 5 个 uv 进程、0 个 uv sync。其他项目进程保持原样。
- 实施验证进程设置 HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1、UV_OFFLINE=1、UV_PYTHON_DOWNLOADS=never。模型缓存指向独立临时 model-cache。HTTP_PROXY、HTTPS_PROXY、ALL_PROXY 指向 http://127.0.0.1:9，NO_PROXY 保留回环地址。未改 CUDA_VISIBLE_DEVICES。
- 以上为进程级离线设置。没有整机断网或防火墙调整，不等同于整机网络隔离。

## 实际 HTTP 与可见浏览器验收

- 独立根目录：C:/Users/lyh/AppData/Local/Temp/tsllm-compare-browser-fejp_b39。
- runs、cache、configs 均位于该临时根目录，配置仅使用合成标识，不读取私有目录。
- 6 个合成终态作业：2 个可比成功预测、1 个失败差异预测、1 个已取消分类、1 个成功入库、1 个失败入库。仅写终态夹具，不执行训练或入库；入库夹具没有 metrics.json。
- 服务实际命令：uv run tsllm serve --port 9000。TSLLM_RUNS_DIR、TSLLM_CACHE_DIR、TSLLM_CONFIGS_DIR 分别指向该临时根目录的 runs、cache、configs；模型缓存使用 hf-empty。沿用四个离线变量、不可用代理及回环例外。启动前 5 个 uv 进程，0 个 uv sync，9000 无监听。
- 首次 Start-Process 后台启动命令被自动审批拒绝，返回 blocked by policy，未提供细项且没有执行。随后使用工具管理的前台会话启动同一隔离服务，保留离线设置，成功监听 127.0.0.1:9000。服务 PID 71532、会话 69120。
- Tabbit 准备阶段的前台能力不可用，未计为应用验收。该空白标签及任务已释放。实际验收使用可见 Codex In-app Browser，document.visibilityState 为 visible。
- 加载的生产文件为 index-DlIxrfbQ.js。截图在会话中实际查看，未写入仓库；检查了警告、状态、ID、表格空值及实际 Canvas 柱状图。

### HTTP 组合

主会话通过实际 9000 HTTP 服务执行以下断言；结果保存在临时根目录 http-acceptance.json。

| 组合 | 状态 | 列数 | 指标行数 | 警告 |
| --- | --- | --- | --- | --- |
| 两个可比成功实验 | 200 | 2 | 4 | 空列表 |
| 单个成功入库 | 200 | 1 | 0 | 1 条入库警告 |
| 两个入库，其中一个失败 | 200 | 2 | 0 | 1 条状态警告、2 条入库警告 |
| 实验在前、入库在后 | 200 | 2 | 4 | 1 条入库警告 |
| 入库在前、实验在后 | 200 | 2 | 4 | 1 条入库警告 |
| 入库、实验、重复入库 ID | 200 | 2 | 4 | 去重后 1 条入库警告 |

每个请求同时断言输入去重后的列顺序、新警告的 ID 顺序及入库指标为 null。启动服务前与全部请求后的 16 个合成作业文件 SHA-256 完全相同；模型缓存文件数为 0。没有排队作业或训练/入库进程。

### 可见页面

| 场景 | 宽度与观察 | 结果 |
| --- | --- | --- |
| 6 作业手工混合链接 | 1280 px；11 条警告覆盖全部 7 码，含 3 个未成功运行、test/val 两个划分及 2 个入库 | 全部中文主要说明、运行 ID、状态和原消息可辨认；保留全部列，入库指标为“—” |
| 同一手工链接 | 390 px；11 条警告均检查宽高，长 ID 与原消息自然换行 | 每个警告 scrollWidth/clientWidth、scrollHeight/clientHeight 相等，无文本裁切 |
| 运行列表入口 | 分别在 390 px、1280 px 检查并操作 | 2 个入库复选框禁用；选择 2 个成功实验后进入对比，URL 保留所选 ID，0 条警告 |
| 对比选择器 | 两个宽度均打开下拉框 | 候选仅包含实验；手工 URL 中已有入库仍保留 |
| 正常实验结果 | 两个宽度均目视检查 | 指标值与顺序保持，Canvas 柱状图可见 |
| 全入库手工链接 | 1280 px 核对内容，390 px 目视检查 | 3 条警告；2 列保留；指标显示“暂无数据”，没有指标图表 |

布局稳定后的页面级 scrollWidth/clientWidth：1280 px 视口为 1265/1265，390 px 视口为 375/375。表格可在自身区域横向滚动。视口刚从 1280 改为 390 时，图表曾保留上一宽度；下一次检查已由 ResizeObserver 更新至 302 px，页面宽度恢复至 375。稳定布局通过，未修改图表或样式以掩盖测量。浏览器控制台 error/warn 记录为空。

完成后恢复浏览器默认视口并关闭本任务标签。通过本会话 Ctrl+C 关闭服务，日志显示 Application shutdown complete / Finished server process；控制台会话因手动中断返回 1。再次核对 PID 71532 已不存在，9000 无监听，未终止其他进程。

## 自动检查与独立审查

| 命令或检查 | 实际结果 |
| --- | --- |
| uv run pytest tests/service/test_api_compare.py | 16 passed、1 warning |
| pnpm -C web exec vitest run tests/pages/ComparePage.test.tsx | 8 passed |
| uv run ruff check | 通过，退出码 0 |
| uv run ruff format --check | 109 files already formatted，退出码 0 |
| uv run pyright | 0 errors、0 warnings、0 informations，退出码 0 |
| uv run pytest | 180 passed、5 deselected、3 warnings，53.24 s，退出码 0 |
| pnpm -C web run check | 46 文件通过，退出码 0 |
| pnpm -C web run test | 5 文件、27 测试通过，退出码 0 |
| pnpm -C web run build | 通过，退出码 0 |
| git diff --check | 通过 |
| git ls-files -- data ref runs cache | 空输出 |
| task.py validate | implement.jsonl 11 条、check.jsonl 10 条通过 |

独立 trellis-check 代理审查全部 8 个产品/测试/生成文件及 2 个规范文件，没有产品发现、没有修复、没有阻断项。独立重新运行后端四门槛；前端复用实施阶段已核对的门槛日志，期间产品代码未变化。后续生成文件的当前哈希与两轮记录一致。

独立检查前 7 个 uv 进程、0 个 uv sync。使用独立 HF/Hub/Torch/XDG 空缓存、四个离线变量、不可用代理及回环例外；不改 CUDA_VISIBLE_DEVICES。模型缓存前后文件数均为 0。

证据目录：

- 实施：C:/Users/lyh/AppData/Local/Temp/tsllm-compare-implement-20260930-cf5d0288/，包含前后回归、ruff、pyright、web-check/test/build 和生成哈希日志。
- 独立检查：C:/Users/lyh/AppData/Local/Temp/tsllm-compare-check-20260930-434f281b/，包含 environment.json、results.json、reviewed-file-hashes.json 和四项后端日志。

### 保留的既有提示

- pytest：Starlette/httpx 弃用提示 1 项，Chronos CPU 微调提示 2 项。默认套件的合成微型模型 CPU 检查已运行。
- 前端测试：jsdom getComputedStyle 伪元素提示；27 项均通过。
- Vite：主块 2,419.86 kB，gzip 785.11 kB。体积提示保持，未提高阈值或实施拆包。

## 生成契约

连续两轮均按以下顺序：官方 uv run tsllm api openapi --out web/openapi.json → pnpm -C web run gen:api → 仅两份生成文件按仓库规则规范为 LF。没有修改 CLI。最终字节逐一比较相同，当前文件哈希与记录一致：

| 文件 | SHA-256 |
| --- | --- |
| web/openapi.json | 19551DD7600E92BB4F4F5E5162B5275ADA2E929ADCC716B1C458DE8BDBAA00DF |
| web/src/api/schema.d.ts | 1F31EA208A2F7DC4ED4C3BCB85FE581DF66E18BFCD74497F3743DEF868AA4D34 |

差异仅为 CompareWarningOut 的两个批准可选字段，code 继续为开放字符串。

## AC1–AC8 结论

| AC | 结论 | 证据 |
| --- | --- | --- |
| AC1 | 通过 | 页面七码英文响应回归；真实页面 11 条警告、3 个未成功运行、test/val 上下文可见 |
| AC2 | 通过 | 接口 16 项覆盖组合和顺序；实际 HTTP 6 组合均为 200，警告计数正确 |
| AC3 | 通过 | 接口文件快照断言；实际 HTTP 空值/空行/列顺序及 16 文件哈希不变 |
| AC4 | 通过 | 接口正常/去重/404/422 回归；两个浏览器入口正常实验无警告 |
| AC5 | 通过 | 页面旧响应、null/缺上下文、未知码、缺列和完全重复警告用例；独立检查确认无英文解析 |
| AC6 | 通过 | 可见 IAB 两种宽度、两种入口、选择限制及稳定布局测量 |
| AC7 | 通过 | 旧消息精确断言、模型默认值及描述、生成差异与双轮最终哈希 |
| AC8 | 通过 | 七项正式门槛、独立全范围检查、差异与私有目录跟踪检查、以下边界声明 |

## 未执行与交付边界

- 未运行真实数据实验、真实入库、真实训练、GPU/weights 标记验收或权重下载。
- 未重复父任务整套集成验收，未修改其完成结论。没有整机断网或防火墙验证。
- 未验证仓库外采用严格响应字段校验的客户端。旧/未知响应降级已由 fetch 层页面测试覆盖，未使用浏览器伪造网络响应。
- 未读取或处置 cache/datasets/ETTh1.acc-backup；没有修改私有目录、.claude/launch.json、依赖、锁文件、构建阈值或 GitHub 设置。
- 实施验收结束时没有提交、推送、合并、发布或归档，任务保留 in_progress。后续用户已单独授权本地收尾；该阶段记录见文末。

## 实际修改范围

8 个产品/测试/生成文件、2 份规范及本任务文档。无其他任务文件或归档父任务改动。基线 HEAD 保持 7829f557c1aac4d356a2a829b010eaa23de5ebed。

## 本地收尾复核（2026-09-30，America/Chicago）

用户本轮明确授权提交本任务产品、规范及当前任务目录内的全部材料，随后归档、修正归档引用并记录开发者日志。实施阶段的授权限制保留为历史记录，以本节最新授权为准。

### 工作提交前的核对

- 分支为 codex/compare-warnings。HEAD、main、本地 origin/main 与 git ls-remote 查询的实际远端 main 均为 7829f557c1aac4d356a2a829b010eaa23de5ebed；远端没有 codex/compare-warnings。
- 暂存区起初为空；完整工作区包含 8 个产品/测试/生成文件、2 份规范及本任务 8 个材料文件，合计 18 个路径。逐一核对范围、UTF-8 文本及大小，包含新增 CompareWarnings.tsx 和全部未跟踪任务材料；无额外改动。
- 唯一未归档任务为 compare-warnings，状态 in_progress。本收尾会话没有活动任务指针，按用户指定目录继续；未创建或重新激活任务。
- 下表 10 个 SHA-256 均与独立检查 reviewed-file-hashes.json 相同。生成文件亦匹配两轮 generated-final-hashes.json；前端原始 check/test/build 日志及后端 results.json 与已记录结果一致。
- 复用七项正式门槛、独立检查、实际 HTTP 六种组合、16 个合成作业文件不变、390/1280 px 两种入口和七码展示、双轮生成一致性证据。本轮无产品修改，不重跑应用验收，不启动服务，不调用 uv。
- 新执行 git diff --check、task.py validate（implement 11 条、check 10 条）和完整差异范围核对；git ls-files -- data ref runs cache 为空。显式暂存后 git diff --cached --check 通过，覆盖所有新增文件；暂存区之外没有本任务遗留改动。

### 复用证据对应的文件哈希

| 文件 | SHA-256 |
| --- | --- |
| src/tsllm/runs/compare.py | 3FBCB87CE74388CEC4424702487745FCB2F571DC4DB257DEB57BB47BC8D984C5 |
| src/tsllm/service/models.py | DAD6FC4E9CBB975FCE72945752A8B0FBA09A75BF26FA439A296D2E814B366DF4 |
| tests/service/test_api_compare.py | 0A930F4F24D45BB482A291279703EDE61B572F45FB91DE9AE504734CADD0CA53 |
| web/openapi.json | 19551DD7600E92BB4F4F5E5162B5275ADA2E929ADCC716B1C458DE8BDBAA00DF |
| web/src/api/schema.d.ts | 1F31EA208A2F7DC4ED4C3BCB85FE581DF66E18BFCD74497F3743DEF868AA4D34 |
| web/src/components/CompareWarnings.tsx | 9D65D39A9943733D4B2214B8A28502E391C5951FF3E188300239ABBF69ADCDDC |
| web/src/pages/ComparePage.tsx | 92CB05F8D9621C39E0CB13B2068D4C845528A0A0D090A841E1113A46F2EAB353 |
| web/tests/pages/ComparePage.test.tsx | 0CF8C893027ADFA096A575B7BE98E9717E67EAECB11B35C162283A41B0716521 |
| .trellis/spec/backend/error-handling.md | 09F976E94AC1ABBC6417F78C8EAE2FC349FFD6225D2AEDDF8567CCC0D5AC343A |
| .trellis/spec/frontend/forms-and-charts.md | 896D50A048C42A939C1E0AB78D6E7BDD952585ADCD6F834FF5F013972CD5297F |

归档时后端规范仅更新本任务设计文件的引用路径；表中哈希对应已验收的归档前内容，原值保留。归档后的产品文件仍须保持字节不变。

### 本轮边界

- 未执行真实数据实验、真实训练、真实入库、GPU/weights 验收、权重下载、依赖安装或新的浏览器/HTTP 验收；既有进程级离线证据不扩展为整机隔离。
- 未读取备份内容或处置 cache/datasets/ETTh1.acc-backup；不修改 .claude/launch.json、私有目录、构建体积阈值、依赖、锁文件及归档父任务。
- 不合并、不推送、不创建 PR、不发布、不删除分支、不创建任务。下一候选为“前端加载影响与拆分收益评估”，仅留待用户另行选择。

### 归档执行

- 工作提交：1060a432e384b96d326ce4e5530809b17ef4532d，包含 8 个产品/测试/生成文件、2 份规范和 8 份任务材料；提交后工作区干净。
- 正式命令 python .trellis/scripts/task.py archive 09-29-compare-warnings --no-commit 成功，退出码 0。主动使用 --no-commit，将归档移动、状态更新及引用修正放入同一个独立归档提交；没有发生自动提交失败。
- 八份材料移动到 .trellis/tasks/archive/2026-09/09-29-compare-warnings；原目录已不存在，状态 completed，completedAt 为 2026-09-30，commit 字段记录工作提交。
- 仅修正后端 error-handling.md 的设计引用，以及 implement.jsonl、check.jsonl 的调查依据路径；归档父任务和其他历史文档不变。
- 后续日志使用 add_session.py，引用工作提交，独立提交在归档提交之后。最终会话记录位于 .trellis/workspace/lyh/journal-1.md 的“对比警告本地收尾与归档”条目。
