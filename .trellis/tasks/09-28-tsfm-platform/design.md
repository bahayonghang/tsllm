# 平台总体设计

本文件定义各子任务共享的边界与契约。子任务的 `design.md` 只细化自身模块，不得修改本文件中的契约；需要修改时先改本文件并同步受影响的子任务。

## 1. 分层与依赖方向

```text
web/ (React)  ──HTTP/SSE──▶  tsllm.service (FastAPI)
                                   │ 读写运行目录、启动子进程
                                   ▼
                     tsllm.runs (worker、run store)
                                   │
              ┌────────────────────┼─────────────────────┐
              ▼                    ▼                     ▼
       tsllm.tasks          tsllm.evaluation       tsllm.backbones
   (forecast / classify)       (metrics)        (adapters, registry)
              │                                        │
              └───────────────▶ tsllm.data ◀───────────┘
                          (contract, windows)
                                   │
                           tsllm.config（Pydantic 模型，所有层共用）
```

规则：

- 依赖只能向下。`tsllm.data` 不导入 torch 和任何模型库。
- `tsllm.backbones` 只依赖 `tsllm.data` 的批次结构和 `tsllm.config`，不读取文件、不知道划分名称以外的数据细节。
- `tsllm.service` 不导入 torch 和模型库；训练与推理只在 worker 子进程中执行。服务进程可以在无 GPU 的环境中启动。
- 模型库（chronos、transformers、tsfm_public、peft）只在适配器的 `load()` 或方法内部导入，注册表导入时不触发。

## 2. 目录布局

```text
pyproject.toml
configs/
  datasets/            # 数据集 YAML，每个数据集一个文件
  runs/                # 运行配置样例与模板
src/tsllm/
  __init__.py          # main() 转调 cli
  cli.py               # typer 命令入口
  reporting.py         # Reporter 协议与简单实现
  errors.py            # TsllmError 基类（带 code）；各领域异常在所属模块中继承它
  config/              # Pydantic 模型、YAML 读写、schema 导出
  data/                # 读取、清洗、重采样、分段、划分、窗口、标签、缓存
  backbones/           # base.py、registry.py、各适配器模块
  tasks/               # forecast.py、classify.py、registry.py
  evaluation/          # metrics.py
  runs/                # store.py（目录与状态）、worker.py（子进程入口）、env.py（环境快照）
  service/             # app.py、jobs.py、routes/*.py
tests/                 # pytest；fixtures 生成合成数据
web/                   # Vite + React + TypeScript
runs/                  # 运行目录（gitignore）
cache/                 # 数据缓存（gitignore）
```

## 3. 配置模型（`tsllm.config`）

全部为 Pydantic v2 模型，`extra="forbid"`。YAML 与 JSON 使用同一模型。

### 3.1 DatasetConfig

```yaml
id: yangquan_kiln # 唯一，文件名与之一致
source:
  path: data/阳泉回转窑联合训练孪生样本/data_in.csv
  format: csv # csv | parquet
  encoding: utf8 # utf8 | utf8-lossy（weather.csv 表头含非 UTF-8 字节）
  time_column: DateTime
  time_format: null # null 表示 ISO 自动解析
native_freq: 10s
freq: 1min # 重采样目标；与 native_freq 相同时不重采样
aggregation: mean # mean | last
dedup: keep_last # keep_first | keep_last
channels: # null 表示全部数值列，角色 target
  - { name: 窑喂料反馈, role: target, unit: null, description: null }
  # ... 共 18 项
eligibility: # null 表示所有非全空行有效
  all:
    - { channel: 窑头煤反馈, op: gt, value: 5 }
    - { channel: 高温风机反馈, op: gt, value: 200 }
segments:
  max_gap: 2min # 相邻有效点间隔超过该值则断段
  min_length: 6h # 短于该值的段丢弃
split:
  ratios: [0.70, 0.10, 0.10, 0.10] # fit, val, cal, test
  basis: eligible_points # 按有效点累计数确定时间边界
```

通道角色枚举：`target`、`past_covariate`、`known_future_covariate`、`ignore`。本轮预测任务只使用 `target` 与 `past_covariate`；`known_future_covariate` 在配置中可写，任务层遇到时报错并提示未实现。

### 3.2 RunConfig

```yaml
name: chronos2-lora-kiln
dataset: yangquan_kiln # 数据集 id
task:
  type: forecast # forecast | classify（判别字段）
  context_length: 120 # 以 dataset.freq 为步长
  horizon: 30
  eval_leads: [5, 15, 30]
  eval_splits: [val, test]
  train_origin_stride: 1
  eval_origin_stride: 30
  max_eval_origins: null # null 表示不限
backbone:
  name: chronos2 # 注册表键
  checkpoint: amazon/chronos-2 # HF 名称或本地目录
  revision: null # null 时运行记录警告并写入解析到的 commit
  device: cuda # cuda | cpu
  dtype: bf16 # fp32 | bf16
  options: {} # 由适配器自身的 Options 模型校验
mode: lora # zero_shot | lora | head | full（取值受基座能力约束）
finetune: # mode 为 zero_shot 时忽略
  learning_rate: 1.0e-5
  num_steps: 1000
  batch_size: 64
  lora: { r: 8, alpha: 16, dropout: 0.05, target_modules: null }
seed: 0
notes: ""
```

分类任务的 `task` 段：

```yaml
task:
  type: classify
  context_length: 120
  eval_splits: [val, test]
  train_origin_stride: 5
  eval_origin_stride: 10
  label:
    type: future_event
    channel: 烟室NOX反馈
    op: gt # gt | lt | outside
    threshold: { quantile: 0.95 } # {quantile: q} 从拟合段有效点计算，或 {value: x}
    window: 30 # 起点之后的步数
    min_duration: 3 # 连续满足的最少步数
  head: { type: logistic, class_weight: balanced } # logistic | mlp
```

分类任务的 `mode` 固定为 `head`（冻结基座，只训练分类头）。模式与基座能力的校验规则见第 5 节。

### 3.3 schema 导出

`tsllm.config.schema.run_config_schema()` 返回 `{"run_config": <RunConfig JSON Schema>, "backbone_options": {backbone_name: options_schema}}`。服务层原样返回，网页据此渲染表单。基座能力、许可与安装状态由 `/api/backbones`（`BackboneInfo` 列表）提供。

## 4. 数据层契约（`tsllm.data`）

### 4.1 PreparedFrame

入库产物为一个 Parquet 文件和一个 JSON 元数据文件，路径 `cache/datasets/<id>/<config_hash>/`：

| 列           | 类型         | 含义                                                       |
| ------------ | ------------ | ---------------------------------------------------------- |
| `time`       | datetime[us] | 规则网格时间，重采样时取区间右端点（该时刻数据已全部可用） |
| 各通道       | float32      | 物理值，缺失为 null                                        |
| `observed` | bool | 该网格区间内至少有一条原始记录 |
| `eligible` | bool | 满足有效性规则；规则引用的通道为 null 时为 false |
| `segment_id` | int32 | 连续段编号；段外为 -1。段从第一个有效点延伸到最后一个有效点，内部连续的无效或未观测行不超过 `max_gap` |
| `split` | categorical | fit / val / cal / test，按时间边界对所有行赋值 |

元数据 `meta.json`：数据集配置哈希、源文件大小与修改时间、行数、各划分时间边界、段列表（起止时间、长度）、通道统计。

重采样规则：区间 `(T - freq, T]` 的聚合值记在 `T`。该规则保证 `T` 时刻的值不含 `T` 之后的原始记录。重采样后补齐到完整规则网格，无原始记录的网格行各通道为 null、`observed` 为 false。

FitStats 与标签阈值只用 `split == fit` 且 `eligible` 的行计算。窗口只要求所有行同属一个段，不要求每一行都 `eligible`。

### 4.2 FitStats

只用 `split == fit` 且 `eligible` 的行计算：每通道均值、标准差、分位数（0.01、0.05、0.5、0.95、0.99）。写入运行目录 `fit_stats.json`。

### 4.3 窗口

- 起点 `o` 为上下文最后一步的行号。上下文为 `[o - L + 1, o]`，目标为 `[o + 1, o + H]`。
- 上下文与目标的所有行必须同属一个 `segment_id`。
- 训练起点：目标所有行的 `split == fit`。
- 评价起点（划分 s）：目标所有行的 `split == s`；上下文可落在更早的划分。
- 清单为 polars DataFrame：`origin_row`、`origin_time`、`segment_id`、`split`。

### 4.4 批次结构（传给适配器）

```python
@dataclass(frozen=True)
class ContextBatch:
    values: np.ndarray        # (B, C, L) float32，缺失为 NaN，物理单位
    channel_names: list[str]
    origin_time: np.ndarray   # (B,) datetime64[us]
    freq: str

@dataclass(frozen=True)
class SegmentSet:            # 微调用：拟合段内的连续段
    arrays: list[np.ndarray]  # 每个 (C, T_i) float32
    channel_names: list[str]
    freq: str
```

目标值与目标掩码只在任务层使用，不传给适配器的 `forecast()`。

## 5. 适配器契约（`tsllm.backbones`）

```python
class Capabilities(BaseModel):
    forecast_modes: set[Literal["zero_shot", "lora", "head", "full"]]   # 空集表示不支持预测
    embed: bool                     # True 表示支持冻结表示提取（分类任务的前提）
    quantiles: bool
    multivariate: Literal["native", "channel_independent", "none"]
    max_context: int | None
    max_horizon: int | None
    needs_fit_stats: bool           # True 表示适配器需要外部缩放统计

class ForecastOutput(BaseModel):   # 实际实现为 dataclass，字段如下
    mean: np.ndarray                # (B, C, H)，物理单位
    quantiles: np.ndarray | None    # (B, C, H, Q)
    quantile_levels: list[float] | None

class Backbone(Protocol):
    name: ClassVar[str]
    capabilities: ClassVar[Capabilities]
    Options: ClassVar[type[BaseModel]]
    def load(self, cfg: BackboneConfig, fit_stats: FitStats | None) -> None: ...
    def forecast(self, batch: ContextBatch, horizon: int) -> ForecastOutput: ...
    def finetune(self, train: SegmentSet, val: SegmentSet | None, cfg: FinetuneConfig,
                 context_length: int, horizon: int, reporter: Reporter) -> None: ...
    def embed(self, batch: ContextBatch) -> np.ndarray: ...     # (B, D)
    def save_adapter(self, path: Path) -> None: ...
    def load_adapter(self, path: Path) -> None: ...
```

- 注册：`@register_backbone` 装饰类；`registry.list_backbones()` 返回名称、能力、Options schema、依赖是否已安装（用 `importlib.util.find_spec` 判断，不导入）。
- 不支持的方法抛 `CapabilityError`。
- `Reporter` 定义在 `tsllm/reporting.py`（Protocol + `NullReporter` + `PrintReporter`），方法为 `log(msg, level="info")`（level 为 `debug | info | warning | error`）、`progress(step, total)`、`metric(name, value, step=None)`、`stage(name)`。数据入库、适配器与 worker 共用。适配器不直接写运行目录。
- 模式含义：`zero_shot` 不训练；`lora` 在基座上加 LoRA 参数；`full` 训练全部参数（岭回归为从零拟合）；`head` 冻结基座、只训练预测头。
- 任务层校验：预测任务要求 `RunConfig.mode ∈ forecast_modes`；分类任务要求 `embed == True`，`RunConfig.mode` 固定为 `head`，含义为冻结基座、只训练分类头。
- 本轮注册名：

| 名称 | forecast_modes | embed | 说明 |
|---|---|---|---|
| `persistence` | zero_shot | 否 | 上下文最后一个非缺失值 |
| `ridge` | full | 否 | 多输出岭回归，`finetune()` 在拟合段上训练 |
| `features` | 无 | 是 | 每通道均值、标准差、最后值、斜率、最小值、最大值 |
| `chronos2` | zero_shot, lora, full | 是 | Chronos-2 |
| `timesfm25` | zero_shot, lora | 是 | TimesFM 2.5，通道独立 |
| `ttm` | zero_shot, head | 否 | Granite TTM；`head` 为冻结主干、训练预测头 |

## 6. 运行目录契约（`tsllm.runs`）

每个运行目录对应一个作业（job）。作业种类有两种：`experiment`（一次预测或分类运行）与 `ingest`（一个数据集入库）。两者共用目录布局、状态机、事件流和任务队列；`ingest` 作业只写 `config.yaml`、`status.json`、`events.jsonl`、`env.json`。

`config.yaml` 为 `JobSpec`：

```yaml
kind: experiment          # experiment | ingest
dataset: {...}            # DatasetConfig 快照（提交时的完整配置）
run: {...}                # RunConfig；kind 为 ingest 时为 null
```

```text
runs/<run_id>/                  # run_id = <YYYYmmdd-HHMMSS>-<name 的 slug>-<4 位随机>
  config.yaml                   # JobSpec
  status.json                   # {"state", "created_at", "started_at", "finished_at", "pid", "error"}
  events.jsonl                  # 每行 {"ts", "kind": "log|progress|metric|stage", ...}
  env.json                      # Python、torch、CUDA、GPU、各模型库版本、checkpoint 与 revision
  fit_stats.json
  label_info.json               # 分类任务：规则、阈值、各划分正类比例
  metrics.json                  # 见 6.1
  predictions/<split>.parquet   # 见 6.2
  adapter/                      # 适配权重或分类头
```

状态机：`queued → running → succeeded | failed | cancelled`；服务重启时 `running` 且进程不存在 → `interrupted`。允许的转换与写入者：

| 起始状态 | 目标状态 | 写入者 | 场景 |
| --- | --- | --- | --- |
| （无） | `queued` | service、CLI | 创建运行目录 |
| `queued` | `running` | worker | worker 启动 |
| `running` | `succeeded` | worker | 正常结束 |
| `running` | `failed` | worker | 捕获到异常 |
| `running` | `failed` | service | 子进程退出码非 0 且状态仍为 `running`（worker 未能写入终态） |
| `queued`、`running` | `cancelled` | service | 用户取消 |
| `running` | `interrupted` | service | 服务启动时发现无存活 worker |

CLI 直接运行时，CLI 进程同时承担 service 角色创建目录，随后以 worker 角色执行。

### 6.1 metrics.json

```json
{
  "task": "forecast",
  "splits": {
    "test": {
      "overall": {
        "mae_norm_macro": 0.0,
        "rmse_norm_macro": 0.0,
        "pinball": 0.0,
        "coverage_80": 0.0,
        "width_80": 0.0
      },
      "per_channel": { "<channel>": { "mae": 0.0, "rmse": 0.0 } },
      "per_lead": { "5": { "mae_norm_macro": 0.0 }, "15": {}, "30": {} },
      "n_origins": 0,
      "origin_set_hash": "sha256 前 12 位，对起点时间序列计算"
    }
  },
  "resources": {
    "load_seconds": 0.0,
    "peak_vram_mb": 0.0,
    "latency_ms_p50": 0.0,
    "latency_ms_p95": 0.0,
    "train_seconds": 0.0
  }
}
```

分类任务 `overall` 字段：`auroc`、`auprc`、`f1`、`brier`、`positive_rate`、`confusion`（2×2）、`threshold`（在验证集选定的判决阈值）；另有 `curves.roc`（`[[fpr, tpr], ...]`）与 `curves.pr`（`[[recall, precision], ...]`），各降采样到不超过 200 点。

`origin_set_hash` 用于对比：两个运行的同一划分哈希不同，说明评价起点集合不同，对比页必须显示警告。

### 6.2 predictions parquet

- 预测：长表 `origin_time, channel, lead, y_true, y_pred, q_<level>...`。
- 分类：`origin_time, label, score`。

## 7. 服务契约（`tsllm.service`）

| 方法     | 路径                          | 说明                                                              |
| -------- | ----------------------------- | ----------------------------------------------------------------- |
| GET      | `/api/health`                 | 存活检查                                                          |
| GET      | `/api/system`                 | GPU、版本、运行目录路径                                           |
| GET      | `/api/schema/run-config`      | RunConfig schema + 各基座 Options schema                          |
| GET      | `/api/datasets`               | 数据集列表与入库状态                                              |
| GET      | `/api/datasets/{id}`          | 配置与 meta                                                       |
| POST     | `/api/datasets/{id}/ingest`   | 以运行形式提交入库（子进程）                                      |
| GET      | `/api/datasets/{id}/series`   | 降采样后的曲线数据，参数 `channels`、`start`、`end`、`max_points` |
| PUT      | `/api/datasets/{id}/channels` | 更新通道字典（写回 YAML）                                         |
| GET      | `/api/backbones`              | 注册表内容                                                        |
| GET/POST | `/api/runs`                   | 列表 / 提交 RunConfig                                             |
| GET      | `/api/runs/{id}`              | 配置、状态、env                                                   |
| POST     | `/api/runs/{id}/cancel`       | 取消                                                              |
| GET      | `/api/runs/{id}/events`       | SSE，支持 `Last-Event-ID` 续读（事件序号为 events.jsonl 行号）    |
| GET      | `/api/runs/{id}/metrics`      | metrics.json                                                      |
| GET      | `/api/runs/{id}/predictions`  | 参数 `split`、`channel`、`origin_time`；不带 `origin_time` 时返回该划分的起点列表（`limit` 默认 500） |
| GET      | `/api/compare`                | 参数 `run_ids`，返回对齐后的指标表与可比性警告                    |
| GET      | `/api/run-templates`          | `configs/runs/*.yaml` 列表                                        |
| GET/PUT  | `/api/run-templates/{name}`   | 读取 / 保存运行配置模板（写入 `configs/runs/<name>.yaml`）        |

错误响应统一为 `{"error": {"code": str, "message": str, "detail": object | null}}`。

## 8. 执行流程

1. 网页提交 RunConfig → 服务校验（Pydantic + 基座能力 + 数据集已入库）→ 创建运行目录（`queued`）→ 入队。
2. 执行器取出任务 → 启动 `<python> -m tsllm.runs.worker <run_dir>`。`<python>` 默认 `sys.executable`，适配器可在注册信息中声明独立解释器路径（本轮只用默认值）。
3. worker：写 `running` → 环境快照 → 读 PreparedFrame → FitStats → 窗口 → 任务执行 → 指标与预测 → `succeeded`；异常时写 `failed` 与错误摘要。
4. 服务通过读取 `events.jsonl` 向网页推送 SSE。
5. 取消：服务终止子进程树，写 `cancelled`。

## 9. 取舍

| 决策         | 选择                     | 理由                                                   |
| ------------ | ------------------------ | ------------------------------------------------------ |
| 运行记录存储 | 文件目录，无数据库       | 运行数量为数百级；文件可直接检查与备份；服务重启可恢复 |
| 训练执行位置 | 子进程                   | 隔离显存与崩溃；取消可靠；允许不同解释器               |
| 配置系统     | Pydantic + YAML          | 同一模型同时用于校验、CLI、API 和网页 schema           |
| 数据处理     | polars + Parquet         | 690 万行 CSV 读取与重采样需要列式处理                  |
| 分类方法     | 冻结表示 + 分类头        | 所有具备 `embed` 能力的基座可直接复用；与预测微调解耦  |
| 实验追踪     | 不接入 MLflow 等外部系统 | 本轮范围只需要本地对比；运行目录可在以后导出           |

## 10. 与参考仓库和报告的关系

报告 8.5 节建议的目录（`data_contract/`、`backbones/`、`adapters/`、`quality/`、`training/`、`evaluation/`、`serving/`）按本平台范围映射为 `data/`、`backbones/`、`tasks/`、`evaluation/`、`runs/`、`service/`。`adapters/`（多变量残差适配器）与 `quality/` 本轮不建。
