# 数据契约与数据集注册

父任务：`.trellis/tasks/09-28-tsfm-platform/`。共享契约见父任务 `design.md` 第 3.1、4 节。

## 目标

把任意单表时序 CSV（首个为阳泉回转窑 DCS 数据）转为规则网格上的 PreparedFrame，并提供窗口清单、批次提取、拟合段统计和规则派生标签。本子任务同时建立项目工具链（依赖、lint、类型检查、测试、CLI 骨架）。

## 需求

- R1 项目工具链：`pyproject.toml` 加入本子任务所需依赖（polars、pyarrow、numpy、pydantic、pyyaml、typer）与 dev 依赖组（ruff、pyright、pytest）；配置 ruff、pyright、pytest；`.gitignore` 加入 `runs/`、`cache/`；`tsllm` 命令入口转到 typer。
- R2 `tsllm.config` 包：公共基类（`extra="forbid"`）、时长字段解析（`10s`、`1min`、`6h`）、`DatasetConfig`（父设计 3.1，含 `encoding`）。
- R3 数据集注册：扫描 `configs/datasets/*.yaml`，按 `id` 读取；`id` 与文件名不一致时报错。
- R4 读取：CSV 与 Parquet；通道列显式声明为 Float64；时间列解析；`utf8-lossy` 编码支持；重复时间戳按 `dedup` 处理。
- R5 重采样：区间 `(T - freq, T]` 聚合记在 `T`；补齐规则网格；输出 `observed`。`freq` 等于 `native_freq` 时只做网格对齐与补齐。
- R6 有效性与分段：规则条件（`gt`、`ge`、`lt`、`le`、`eq`、`ne`，`all` / `any` 组合）；分段规则见父设计 4.1；丢弃短于 `min_length` 的段。
- R7 划分：按 `basis: eligible_points` 用有效点累计数确定 3 个时间边界，对所有行赋值 `split`。
- R8 缓存：PreparedFrame 写入 `cache/datasets/<id>/<config_hash>/frame.parquet` 与 `meta.json`；配置或源文件（大小、修改时间）变化时判定为过期。
- R9 FitStats：父设计 4.2。
- R10 窗口：父设计 4.3；训练清单支持步长；评价清单支持步长与最大数量（按时间均匀抽取，固定种子）。
- R11 批次提取：`ContextBatch`、目标数组 `(B, C, H)` 与目标掩码、`SegmentSet`（拟合段内的段，按划分边界截断）。
- R12 标签：`future_event` 规则（`gt`、`lt`、`outside`），阈值 `{quantile: q}` 或 `{value: x}`（`outside` 用 `low` / `high`），`window`、`min_duration`；阈值只来自拟合段有效点。
- R13 画像：`meta.json` 含每通道的空值率、有效点统计、段列表、划分边界与各划分有效点数。
- R14 CLI：`tsllm data list`、`tsllm data ingest <id>`、`tsllm data profile <id>`（打印摘要）。入库函数接收 `tsllm/reporting.py` 中定义的 `Reporter`。
- R15 数据集配置文件：`configs/datasets/yangquan_kiln.yaml`（18 通道全部为 `target`，有效性规则与父设计 3.1 一致）、`configs/datasets/ETTh1.yaml`（`channels: null`，无有效性规则）。
- R16 `tsllm/errors.py`：`TsllmError(Exception)`，类属性 `code: ClassVar[str]`。数据层异常继承它：`DatasetNotFound`（`DATASET_NOT_FOUND`）、`DatasetNotIngested`（`DATASET_NOT_INGESTED`）、`DatasetConfigError`（`DATASET_CONFIG_INVALID`）。规则见 `.trellis/spec/backend/error-handling.md`。

## 验收标准

- [x] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过。
- [x] AC2 单元测试覆盖：前 N 行全空的通道被读为浮点；重复时间戳去重；右端点标记（`T` 的值不含 `T` 之后的记录）；网格补齐与 `observed`；`max_gap` 与 `min_length`；划分边界的有效点比例误差不超过 1 行；训练窗口目标全部在拟合段；评价窗口目标在所属划分且上下文可跨入前一划分；窗口不跨段；在测试段注入极端值后 FitStats 与标签阈值不变；`min_duration` 标签计算；缓存过期判定。
- [x] AC3 测试只用 `tests/` 内生成的合成数据，不读取 `data/`。
- [x] AC4 `uv run tsllm data ingest yangquan_kiln` 在本机完成，耗时写入任务备注；`meta.json` 中 1 min 网格上的有效点数与 523,702（= 3,142,212 ÷ 6；用户批准修正后的独立源计数基准）的偏差不超过 2%；段数、各划分边界写入任务备注。
- [x] AC5 `uv run tsllm data ingest ETTh1` 完成，有效点数等于非全空行数。
- [x] AC6 `tsllm.data` 不导入 torch。

## 备注

- 数据画像依据：父任务 `research/data-profile.md`。
- `窑喂料反馈`、`分解炉内温度1反馈` 在默认推断下为 String，必须显式声明类型。

### 本轮实施与本机验收

- 步骤 1–9 已完成。四项命令均退出 0：Ruff check 无诊断；Ruff format 为 `32 files already formatted`；pyright 为 `0 errors, 0 warnings, 0 informations`；pytest 为 `86 passed`。
- 步骤 7 已经独立 trellis-check 审查，8 类泄漏约束变异全部由对应测试检出。详见 `verification.md`。
- `uv run tsllm data ingest yangquan_kiln` 退出 0，完成首次实际读取、重采样和缓存写入。CLI 内计时 **3.138 s**；包含 uv/进程启动的墙钟耗时 **3.805 s**。
- 缓存：`cache/datasets/yangquan_kiln/07c6f11007c2/`。网格行数 **1,254,823**，有原始记录的分钟 **1,152,556**，有效分钟 **523,782**，保留段数 **43**。
- **历史 AC4 失败记录**：有效分钟相对当时基准 460,417 偏差 **+13.762524%**，超过 ±2%，因此暂停后续步骤。该记录保留；有效性规则与入库结果未调整。

划分边界均为源数据的无时区时间：

| 划分 | 起始边界 | 网格行数 | 有效分钟 |
| --- | --- | ---: | ---: |
| fit | 源网格起点 | 866,433 | 366,647 |
| val | 2024-08-24 16:34:00 | 70,237 | 52,378 |
| cal | 2024-10-12 11:11:00 | 246,738 | 52,378 |
| test | 2025-04-01 19:29:00 | 71,415 | 52,379 |

### AC4 差异核对与暂停点

1. 使用既定配置对源文件执行只读核对，仅输出计数与时间元信息，不输出原始通道值。数据层读取/规则计算得到去重后有效行 **3,142,209**。
2. 独立使用 Python 标准库 `csv` 和 `datetime` 逐行核对，不调用 `tsllm.data` 或 Polars。结果：总行 **6,914,135**；原始有效行 **3,142,212**；重复时间戳 **7**；去重后总行 **6,914,128**；去重后有效行 **3,142,209**；时间逆序 **0**。两种方法的去重后有效计数一致。
3. 当前源文件的原始有效行数除以 6 为 **523,702**，与重采样后 523,782 相差 **80** 分钟。研究资料中的原始有效行数为 **2,762,503**；该数值与当前源文件不一致。差异来源原因未查明。
4. 源文件大小 **1,068,005,224 bytes**，`mtime_ns=1790605681207365900`，配置哈希 `07c6f11007c2`。这些元信息来自本次缓存，不能证明研究阶段使用了同一文件内容。
5. 用户已批准按当前源文件的独立计数同步修正父任务 `research/data-profile.md`、本任务 AC4 和 `time-series-guidelines.md` 中的核对基准为 **523,702**，保留 ±2% 容差。父任务共享数据处理契约不变。
6. 原停止门禁的失败证据保留。基准修正获批后继续验证 AC4、执行 AC5、最终审查及 Phase 3.3/3.4；提交与归档仍需另行确认。

### 基准修正后的验收结果

- **AC4 通过**：当前源文件指纹与首次入库缓存一致，`is_fresh` 返回 true；`uv run tsllm data profile yangquan_kiln` 退出 0。有效分钟仍为 **523,782**，相对批准基准 **523,702** 偏差 **+0.015276%**。各划分有效分钟之和与总数一致。首次完整入库耗时与历史失败记录均保留。
- **AC5 通过**：`uv run tsllm data ingest ETTh1` 退出 0，CLI 内计时 **0.038 s**，墙钟耗时 **0.558 s**；网格行数 **17,420**、有效点 **17,420**、段数 **1**。独立标准库 CSV 核对源文件的非全空行数为 **17,420**，与缓存有效点数相等。
- ETTh1 缓存：`cache/datasets/ETTh1/b3ab93028b99/`；源大小 **2,589,657 bytes**，`mtime_ns=1790605676371942900`。
- ETTh1 划分有效点：fit **12,193**、val **1,742**、cal **1,742**、test **1,743**。边界为 val **2017-11-21 01:00:00**、cal **2018-02-01 15:00:00**、test **2018-04-15 05:00:00**，均无时区。
- 最终全范围 trellis-check 已完成。修复缓存写入后源文件变化检测，并新增回归用例。最终四项命令均退出 0：Ruff check 无诊断；format 为 `32 files already formatted`；pyright 为 `0 errors, 0 warnings, 0 informations`；pytest 为 **87 passed**。完整历史与修正证据见 `verification.md`。
- 最终代码对两个数据集执行 `--force` 完整复测。yangquan_kiln：CLI **4.535 s**、墙钟 **6.763 s**、**523,782** 有效分钟、**43** 个保留段。ETTh1：CLI **0.060 s**、墙钟 **0.827 s**、**17,420** 有效点、**1** 个段。写后缓存均 fresh，源指纹、配置哈希和划分边界均不变。
- Phase 3.3 已完成，六项适用后端规范在已实现范围内标记 Verified 并引用真实文件。Phase 3.4 提交方案待用户确认；未暂存、提交、归档或推送。
