# 时序基础模型微调与展示平台

## 目标

建设一个通用的时序基础模型（TSFM）实验平台。平台在同一套数据契约和评价器下，对不同基座模型执行零样本预测、LoRA 微调和基于表示的分类，并通过网页完成配置、启动、监控和结果对比。首个验证数据集为阳泉回转窑 DCS 数据（`data/阳泉回转窑联合训练孪生样本/data_in.csv`）。

## 背景

- 研究方案：`ref/cement_tsfm_research_20260928/`（报告、blueprint、来源清单）。报告建议 TimesFM 2.5 与 Chronos-2 两条 LoRA 路线，TTM 作成本对照。
- 数据画像：`research/data-profile.md`。18 通道、10 s 采样、2023-01-01 至 2025-05-21、运行行占 45.4%、无化验标签、两个 CSV 逐字节相同。
- 依赖与接口核对：`research/library-compatibility.md`。
- 报告条款适用性：`research/report-applicability.md`。报告的质量联合训练在本数据上无法执行。

## 已确认的决策（2026-09-28，用户确认）

| 编号 | 决策 |
|---|---|
| D1 | 网页采用 FastAPI（REST + SSE）+ React / TypeScript / Vite + ECharts；配置表单由后端 Pydantic 模型导出的 JSON Schema 驱动 |
| D2 | 水泥数据首个分类任务为规则派生的未来事件分类（例如未来 30 min 内某通道超过阈值），规则写在配置中 |
| D3 | 预测任务默认 18 个通道全部为目标，不使用未来已知协变量；通道角色写在可编辑的通道字典中 |

## 需求

### R1 通用性

- R1.1 数据集以 YAML 配置注册。新增数据集只需新增配置文件，无需改代码。`data/` 下的 ETT、weather 等 CSV 与水泥数据走同一入口。
- R1.2 基座模型以适配器注册。新增基座只需新增一个适配器模块并注册，无需改任务、评价、服务和网页代码。
- R1.3 任务类型以注册表管理。本轮提供 `forecast` 与 `classify` 两类。
- R1.4 网页的配置表单、基座选项和任务选项全部来自后端 schema，新增基座或任务后网页无需改代码即可配置。

### R2 数据契约（子任务 data-contract）

- R2.1 CSV 转为 Parquet 缓存，显式声明列类型，去除重复时间戳。
- R2.2 按配置重采样到规则网格（水泥默认 1 min），保留缺失掩码。
- R2.3 按配置规则判定有效运行点，按运行状态和时间断点切分连续段。
- R2.4 按原始时间顺序划分拟合 / 验证 / 校准 / 测试（默认 0.70 / 0.10 / 0.10 / 0.10）。
- R2.5 生成窗口清单：上下文与目标位于同一连续段；训练窗口目标全部位于拟合段；评价起点的目标位于所属划分，上下文可使用更早的合法历史。
- R2.6 拟合段统计（均值、标准差、分位数）只用拟合段计算。
- R2.7 规则派生标签只用起点之后的目标窗口计算，阈值只用拟合段计算。

### R3 基座与基线（子任务 backbone-adapters）

- R3.1 统一适配器接口：能力声明、加载、预测、微调、表示提取、保存与加载适配权重。
- R3.2 本轮适配器：Chronos-2（零样本、LoRA、表示）、TimesFM 2.5（零样本、LoRA）、Granite TTM（零样本、头部微调）、保持值基线、岭回归线性基线、手工统计特征（仅表示）。
- R3.3 检查点支持 Hugging Face 模型名与本地目录，支持 `HF_ENDPOINT` 镜像，记录 revision。

### R4 实验运行（子任务 experiment-runner）

- R4.1 单个运行由一个 `RunConfig` 描述，可由 YAML 或 JSON 提交。
- R4.2 预测任务：零样本与 LoRA 微调，按提前量输出物理单位 MAE / RMSE、拟合段尺度归一化宏平均、分位数损失、区间覆盖率与宽度。
- R4.3 分类任务：冻结表示 + 分类头（逻辑回归或 MLP），输出 AUROC、AUPRC、F1、Brier 分数、混淆矩阵与各划分正类比例。
- R4.4 资源指标：峰值显存、单批推理时延 p50 / p95、模型加载时间。
- R4.5 运行记录以文件目录为唯一事实来源：配置、状态、事件流、环境快照、指标、预测结果、适配权重。
- R4.6 CLI 可在无网页的情况下完成数据入库、画像和运行。

### R5 服务（子任务 service-api）

- R5.1 REST 接口覆盖数据集、基座、schema、运行的查询、提交、取消与结果读取。
- R5.2 运行在子进程中执行，GPU 任务默认同一时刻只运行 1 个，其余排队。
- R5.3 SSE 推送运行事件（日志、进度、指标）。
- R5.4 服务重启后恢复运行状态：无存活进程的 `running` 标为 `interrupted`，`queued` 重新入队。

### R6 网页（子任务 web-ui）

- R6.1 数据集页：通道列表与统计、运行段时间轴、划分边界、通道角色编辑。
- R6.2 运行配置页：由 JSON Schema 渲染表单，可保存与加载配置模板，提交运行。
- R6.3 运行监控页：状态、进度、实时日志、取消。
- R6.4 结果页：预测曲线（上下文、真值、预测、分位区间）、按通道与提前量的指标表、分类 ROC / PR 曲线与混淆矩阵。
- R6.5 对比页：选择多个运行，对比指标表与柱状图。

## 约束

- C1 Python 3.13，uv 管理依赖，`src/tsllm` 包布局。
- C2 本机 GPU 为 RTX 5090 Laptop（sm_120），torch 使用 CUDA 12.8 及以上构建。
- C3 `huggingface.co` 直连不可用，下载权重需镜像或本地路径；单元测试不得依赖网络和权重。
- C4 `data/`、`ref/`、运行目录和缓存目录不入库。
- C5 TimesFM-3 不纳入（许可限制）。Toto 2.0、MOMENT、Moirai 本轮不纳入。
- C6 平台只做离线实验，不写入任何控制系统。

## 不在本轮范围

- 质量联合训练、OAM-Net、f-CaO 软测量（缺化验数据）。
- TimesFM 2.5 多变量残差适配器（报告 6.3 节）。
- 过去协变量与未来已知协变量输入。通道字典可以标注这两种角色；运行遇到时报"未实现"。
- 独立校准段上的区间校准算法、显著性重采样、消融矩阵自动化。
- 多用户、权限、远程部署。

## 子任务映射

| 子任务 | 负责需求 | 依赖 |
|---|---|---|
| `00-bootstrap-guidelines` | 填写 `.trellis/spec/` 与 `AGENTS.md` | 无 |
| `09-28-data-contract` | R1.1、R2 | bootstrap |
| `09-28-backbone-adapters` | R1.2、R3 | data-contract 的批次数据结构 |
| `09-28-experiment-runner` | R1.3、R4 | data-contract、backbone-adapters |
| `09-28-service-api` | R5 | experiment-runner |
| `09-28-web-ui` | R1.4、R6 | service-api 的 OpenAPI |

## 跨子任务验收标准

- [ ] AC1 在一台未联网的机器上，`uv run pytest` 通过，测试不下载权重。
- [x] AC2 `uv run tsllm data ingest yangquan_kiln` 生成 Parquet 缓存与画像，画像中的行数、运行段数与 `research/data-profile.md` 的口径一致（重采样后按 1 min 计）。
- [x] AC3 同一份水泥数据上，保持值、岭回归、Chronos-2 零样本、Chronos-2 LoRA、TimesFM 2.5 零样本、TimesFM 2.5 LoRA、TTM 零样本 7 个预测运行使用同一窗口清单与同一评价器完成，结果可在网页对比页并列显示。需要权重的运行在有权重的环境中执行，运行目录记录 revision。
- [x] AC4 同一份水泥数据上，统计特征基线与 Chronos-2 表示两个分类运行完成，标签规则与阈值写入运行记录，阈值来自拟合段。
- [x] AC5 在网页中完成"配置 → 提交 → 监控日志 → 查看结果 → 对比"的完整流程，不使用命令行。
- [x] AC6 新增一个数据集（ETTh1）只需新增一个 YAML 文件；该数据集上的保持值与 Chronos-2 零样本运行可从网页提交并完成。
- [x] AC7 泄漏检查测试覆盖：训练目标不越过拟合段末端、拟合统计与标签阈值只来自拟合段、窗口不跨连续段。

## 备注

### 集成审查状态（2026-09-29）

分支 `codex/web-ui`，验证基线 `e53b17ce8f3b22d50120fd5643d69716996c8c42`。AC2–AC7 已核对并勾选。AC1 的默认套件在进程级离线设置下通过，但原定的未联网机器环境条件尚未验证，保持未勾选。两项缺陷已在工作区修复（见下文“缺陷修复”），尚未提交。统一验证需在提交后用干净克隆重跑，顺序 6 尚未完成。未推送或归档。

### 验收证据

下文子任务引用均位于 `.trellis/tasks/archive/2026-09/`。本轮复用已记录的权重/CUDA、变异、schema、响应式、服务取消及恢复证据，没有重复执行这些检查。

| 验收项 | 证据 |
| --- | --- |
| AC1 | 临时干净克隆的 `uv run pytest`：165 passed、5 deselected、3 warnings。设置 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`UV_OFFLINE=1`，使用独立空 `HF_HOME`；外部 HTTP/HTTPS/ALL 代理指向 `127.0.0.1:9`，保留回环地址例外。没有下载权重。未实施物理断网或防火墙隔离，原始套接字访问不在该隔离证据范围内。 |
| AC2 | 缓存 `cache/datasets/yangquan_kiln/07c6f11007c2/` 为 fresh，未重新入库。Parquet 独立汇总与 `meta.json` 的计数、段数、划分边界一致，网格间隔均为 60 s。复用 `09-28-data-contract/prd.md` 备注与 `verification.md` 的入库验收。 |
| AC3 | 下表 7 个预测目录全部 succeeded，error 为 null；各划分起点逐项等于当前缓存生成的合法清单，预测文件独立重算 hash 与指标一致。统一使用 `src/tsllm/tasks/forecast.py` 的 `forecast_metrics`。网页列表勾选这 7 项后进入对比页，7 项并列显示，可比性警告数为 0。 |
| AC4 | 下表 2 个分类目录全部 succeeded。两项 `label_info.json.rule` 分别等于配置且互相相等；记录阈值均等于独立筛选 `split == fit && eligible` 后的线性分位数。规则和阈值保留于运行记录，本文不抄录物理阈值。复用 `09-28-experiment-runner/prd.md` 的 CLI 验收。 |
| AC5 | 服务 `uv run tsllm serve --port 8000` 托管已有 `web/dist`。在内置浏览器加载模板、修改运行名、预览、提交，观察状态及 SSE 日志，查看成功结果，再勾选两个新运行进入对比页，警告数为 0。提交与对比全程通过网页控件完成。 |
| AC6 | 复用 `configs/datasets/ETTh1.yaml` 及 data-contract、web-ui 的注册和入库证据；当前缓存已存在，未重复入库。本轮从网页提交 persistence 与 Chronos-2 零样本，均成功；后者记录镜像域名与已解析 revision。未新增服务或网页的数据集分支。 |
| AC7 | 下文列出的泄漏测试均包含在本轮 165 项通过的默认套件中。复用 `09-28-data-contract/verification.md` 第 98–109 行的 8 类约束变异全部检出证据，未重复变异检查。 |
| 私有目录 | `git ls-files -- data ref runs cache` 输出为空，跟踪文件数 0；`git check-ignore` 四个根目录均命中。两份临时克隆也没有这四个根目录。 |

### 干净克隆统一验证

默认克隆：`C:/Users/lyh/AppData/Local/Temp/tsllm-integration-20260929-070711-7445c78b/repo`。完整日志、环境记录、`results.jsonl`、`crlf-evidence.json`、`final-integrity.json`、`summary.md` 位于其上一级目录。

工具版本：Python 3.13.11、uv 0.12.19、Ruff 0.16.9、Pyright 1.1.414、pytest 9.1.1、Node 26.7.0、pnpm 12.8.0。

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `uv sync` | 0 | 通过 |
| `uv run ruff check` | 0 | 通过 |
| `uv run ruff format --check` | 0 | 109 个文件通过 |
| `uv run pyright` | 0 | 0 errors、0 warnings |
| 更正额外环境设置后的离线 `uv run pytest` | 0 | 165 passed、5 deselected、3 warnings；测试耗时 57.50 s |
| `pnpm -C web install` | 0 | 通过 |
| `pnpm -C web run check` | 1 | 45 个检查文件中有 44 项 CRLF 格式错误 |
| `pnpm -C web run test` | 0 | 5 个文件、20 项通过 |
| `pnpm -C web run build` | 0 | TypeScript 与构建通过；主块 2,418.61 kB，超过 2,000 kB 阈值 |

首次离线测试额外把 `CUDA_VISIBLE_DEVICES` 设为空字符串，结果为 13 failed、152 passed。独立进程确认该环境下 PyTorch 同时返回 `is_available=true` 和 `device_count=0`，查询设备名报 `Invalid device id`。移除该额外设置、保留全部离线控制后完整默认套件通过。两次日志均保留，未修改产品代码或断言。

默认克隆继承 `core.autocrlf=true`。44 个报错文件与受控 LF 克隆逐字节比较，差异全部为 CRLF。第二个目录为同级 `repo-lf`，通过 `git -c core.autocrlf=false clone` 创建，仅重跑 `pnpm install/check`，均通过。两份克隆最终 `git status --porcelain` 为空，`git diff --check` 通过；未在克隆内编辑代码、配置或锁文件。受控 LF 检查不替代默认克隆的失败记录。

非阻断警告包括 Starlette/httpx 弃用提示、两项 Chronos CPU 训练提示、两项 jsdom 伪元素提示及 Vite 块体积提示。

### AC2 缓存画像与时间边界

1 min 网格共 **1,254,823** 行，有源记录的分钟 **1,152,556**，有效分钟 **523,782**，保留运行段 **43**。有效分钟相对已批准基准 **523,702** 偏差 **+0.015276%**，满足 ±2%。研究画像的 **98 段**属于原始 10 s 数据历史统计；43 段采用重采样后的 `max_gap=2min` 与 `min_length=6h`，对应归档 data-contract 的验收口径。未重新计算或覆盖原始画像。

| 划分 | 起始时间 | 结束时间 | 网格行数 | 有效分钟 |
| --- | --- | --- | ---: | ---: |
| fit | 2023-01-01 00:01:00 | 2024-08-24 16:33:00 | 866,433 | 366,647 |
| val | 2024-08-24 16:34:00 | 2024-10-12 11:10:00 | 70,237 | 52,378 |
| cal | 2024-10-12 11:11:00 | 2025-04-01 19:28:00 | 246,738 | 52,378 |
| test | 2025-04-01 19:29:00 | 2025-05-21 09:43:00 | 71,415 | 52,379 |

数据时间没有时区，表中保持缓存时间。

### AC3、AC4 复用的运行目录

九项全部成功，无缺失运行，无需补跑。

| 运行 | 仓库根目录下的路径 |
| --- | --- |
| persistence | `runs/20260929-084253-kiln-persistence-e589/` |
| ridge | `runs/20260929-084259-kiln-ridge-9d63/` |
| Chronos-2 零样本 | `runs/20260929-082618-kiln-chronos2-zero-shot-8db1/` |
| Chronos-2 LoRA | `runs/20260929-082825-kiln-chronos2-lora-fb72/` |
| TimesFM 2.5 零样本 | `runs/20260929-082710-kiln-timesfm25-zero-shot-b508/` |
| TimesFM 2.5 LoRA | `runs/20260929-083129-kiln-timesfm25-lora-8452/` |
| TTM 零样本 | `runs/20260929-084336-kiln-ttm-zero-shot-c3ce/` |
| 统计特征分类 | `runs/20260929-084307-kiln-classify-features-a42f/` |
| Chronos-2 表示分类 | `runs/20260929-083732-kiln-classify-chronos2-67ff/` |

| 组别 | val 起点数 / hash | test 起点数 / hash |
| --- | --- | --- |
| 7 个预测 | 1,728 / `e51e301e6b09` | 1,735 / `07c9ced03282` |
| 2 个分类 | 5,186 / `53cd5f35e9df` | 5,204 / `024d71566f7f` |

六个需要权重的运行均记录解析 revision：Chronos-2 为 `29ec3766d36d6f73f0696f85560a422f50e8498c`，TimesFM 2.5 为 `5a9806b9b291fad9233b5249d88263f1846304d3`，TTM 为 `6e5cb8ee51e0634a45637490f5db43148b2fa6be`。

### AC5、AC6 网页操作与截图检查

1. 启动服务并打开内置浏览器，用户确认窗格已在前台；截图期间 `document.visibilityState=visible`，页面存在真实 canvas。
2. 加载 `etth1_persistence`，改名为 `parent-ac6-etth1-persistence`，预览后提交。运行 `20260929-120555-parent-ac6-etth1-persistence-7c80` 在 12:05:55–12:05:59 UTC 完成，日志含 load、evaluate:val、evaluate:test、done。
3. 加载 `etth1_chronos2_zero_shot`，改名为 `parent-ac6-etth1-chronos2`，预览固定 revision 后提交。运行 `20260929-120729-parent-ac6-etth1-chronos2-a806` 在 12:07:29–12:07:57 UTC 完成，观察到排队状态及后续日志。服务设置 `HF_ENDPOINT=https://hf-mirror.com`，模型使用本地已缓存检查点；`env.json.backbone.resolved_revision` 与模板的固定 revision 相同。
4. 查看两项结果，网页列表勾选两项并点击“对比所选（2）”。val 均为 69 个起点 / `067cfa98522c`，test 均为 68 个起点 / `b7fffa390b61`，对比警告数为 0。
5. 网页列表勾选上表七项水泥预测，点击“对比所选（7）”，确认七项并列显示，警告数为 0。

截图位置：本次会话的内置浏览器截图工具输出，仅用于目视检查；没有另存截图文件，没有写入仓库路径。截图可能包含现场数据，因此不嵌入本文。

| 截图页面 | 检查结果 |
| --- | --- |
| 本轮 ETTh1 persistence 结果 | 上下文、真值、预测均值与起点线可见 |
| 本轮 ETTh1 Chronos-2 结果 | 上下文、真值、预测均值、10–90% 分位带与起点线可见 |
| 两项 ETTh1、七项水泥预测对比 | val/test 分组柱与图例可见；修复前纵轴标题与顶部图例重叠，修复后复核见“缺陷修复” |
| 历史 Chronos-2 分类结果 | ROC、PR 各有 val/test 曲线，坐标轴与图例可见 |
| 水泥数据集详情 | 运行段时间轴、四色划分带、划分边界、通道曲线与缩放控件可见 |

### 缺陷修复（2026-09-29，未提交）

| 缺陷 | 修改 | 验证 |
| --- | --- | --- |
| 默认 Windows 克隆 44 项 CRLF 格式错误 | `.gitattributes` 新增 `* text=auto eol=lf`。索引内 278 个文本文件原已为 LF，2 个为空文件，无需重新规范化。 | 会话暂存目录中新建默认克隆，`core.autocrlf=true`；把同一规则写入 `.git/info/attributes` 后重新检出 `web/`：48 个文件全部为 `w/lf`，`git status --porcelain` 为空，`pnpm -C web install --frozen-lockfile` 与 `pnpm -C web run check`（45 个文件）通过。该方法模拟规则入库后的检出，尚未替代提交后的干净克隆验证。 |
| 对比柱状图纵轴标题与顶部图例重叠 | `web/src/components/charts/CompareBarChart.tsx`：滚动图例从 `top: 0` 改为 `bottom: 0`，`grid.bottom` 从 32 改为 64。 | 工作区 `pnpm -C web run check`、`test`（5 个文件、20 项）、`build` 通过。重建后在内置浏览器打开七项水泥预测对比页，宽度 640 px：纵轴标题单独位于绘图区上方，图例位于 x 轴标签下方并分页显示（1/3），三者互不重叠。 |

复核服务：Windows 当前排除 TCP 7705–8404 端口段，8000 无法绑定。复核改用被 git 忽略的 `.claude/launch.json` 在 9000 端口启动 `uv run tsllm serve`。

### AC7 泄漏测试映射

| 规则 | 文件与测试名 |
| --- | --- |
| 训练目标留在 fit，窗口同段 | `tests/data/test_stats_windows.py::test_train_targets_stay_fit_and_windows_stay_in_one_segment` |
| 微调数组在 fit 末端截断 | `tests/data/test_stats_windows.py::test_segment_set_truncates_fit_boundary` |
| val/cal/test 极值不改变拟合统计 | `tests/data/test_stats_windows.py::test_fit_statistics_ignore_future` |
| 统计排除无效 fit 行 | `tests/data/test_stats_windows.py::test_stats_ignore_ineligible_fit_rows` |
| 标签阈值只用有效 fit 行 | `tests/data/test_labels.py::test_threshold_ignores_future`、`test_threshold_ignores_ineligible_fit` |
| worker 阈值独立核对与未来极值不变性 | `tests/tasks/test_classify_leakage.py::test_label_threshold_uses_fit_rows_only` |
| 跨段提取必须拒绝 | `tests/data/test_stats_windows.py::test_invalid_extraction_rejected`、`tests/data/test_labels.py::test_illegal_label_window_rejected` |
| 适配器采样不得跨连续数组 | `tests/backbones/test_baselines.py::test_windows_never_cross_arrays` |
| 跨基座评价起点相同 | `tests/tasks/test_origin_hash.py::test_same_task_config_gives_same_origin_sets` |

### 与规划的偏差

- 按用户要求复用 fresh 缓存与九个成功运行，替代重复入库、训练。
- 背景中的 40% 与已批准画像的 45.4% 不一致，本次修正为 45.4%；原始 98 段与重采样 43 段分别注明口径。
- AC1 使用进程级离线控制，未实施物理断网；首次额外 CUDA 屏蔽失败保留为验证环境偏差。
- 默认 Windows 克隆前端格式检查失败；受控 LF 克隆只用于定位原因，未在克隆内格式化或修改代码。
- 可见 canvas 截图补足 web-ui 子任务仅检查 SVG option 的证据边界；截图仅留在会话。

### 遗留问题

- AC1 的未联网机器环境条件尚无证据；现有离线标志、空模型缓存与代理设置仅构成进程级离线验证。未修改原验收条件。
- `.gitattributes` 与 `CompareBarChart.tsx` 的修复尚未提交；提交后需用默认 Windows 干净克隆重跑统一验证命令，再勾选顺序 6 的第一项。
- 规范索引仍有归档前子任务路径，backend 索引仍写 `Web contracts remain Decided`；本次记录差异，未扩大到规范清理。
- `AGENTS.md` 的父任务状态仍写集成证据未记录；该文件在本轮开始前已有未提交改动，本轮未修改。父任务当前状态以本备注为准。
- 继承 web-ui 已记录事项：`ETTh1.acc-backup` 保留；服务对比警告为英文；接口未警告“实验 + 入库作业”组合，但网页已禁止该组合；约 2.4 MB 构建块仍有警告。
