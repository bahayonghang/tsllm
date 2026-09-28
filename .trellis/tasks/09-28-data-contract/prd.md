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

- [ ] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过。
- [ ] AC2 单元测试覆盖：前 N 行全空的通道被读为浮点；重复时间戳去重；右端点标记（`T` 的值不含 `T` 之后的记录）；网格补齐与 `observed`；`max_gap` 与 `min_length`；划分边界的有效点比例误差不超过 1 行；训练窗口目标全部在拟合段；评价窗口目标在所属划分且上下文可跨入前一划分；窗口不跨段；在测试段注入极端值后 FitStats 与标签阈值不变；`min_duration` 标签计算；缓存过期判定。
- [ ] AC3 测试只用 `tests/` 内生成的合成数据，不读取 `data/`。
- [ ] AC4 `uv run tsllm data ingest yangquan_kiln` 在本机完成，耗时写入任务备注；`meta.json` 中 1 min 网格上的有效点数与 460,417（= 2,762,503 ÷ 6）的偏差不超过 2%；段数、各划分边界写入任务备注。
- [ ] AC5 `uv run tsllm data ingest ETTh1` 完成，有效点数等于非全空行数。
- [ ] AC6 `tsllm.data` 不导入 torch。

## 备注

- 数据画像依据：父任务 `research/data-profile.md`。
- `窑喂料反馈`、`分解炉内温度1反馈` 在默认推断下为 String，必须显式声明类型。
