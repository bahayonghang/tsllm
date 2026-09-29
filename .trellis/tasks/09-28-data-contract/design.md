# 数据契约设计

共享契约以父任务 `design.md` 第 3.1、4 节为准。本文件细化模块划分与算法。

## 1. 模块

```text
src/tsllm/
  cli.py                  # typer app；data 子命令组
  reporting.py            # Reporter 协议、NullReporter、PrintReporter（父设计第 5 节）
  config/
    __init__.py
    base.py               # StrictModel(BaseModel, extra="forbid")；Duration 类型（解析 "10s"/"1min"/"6h" 为 timedelta）
    dataset.py            # DatasetConfig、SourceConfig、ChannelSpec、Condition、ConditionGroup、SegmentConfig、SplitConfig
    io.py                 # load_yaml(model, path)、dump_yaml(model, path)
  data/
    __init__.py           # 只导出公共接口
    registry.py           # dataset_dir()、list_datasets()、load_dataset(id)
    source.py             # read_source(cfg) -> pl.DataFrame
    rules.py              # evaluate(condition_group, frame) -> pl.Series[bool]
    prepare.py            # prepare(cfg) -> PreparedFrame；resample、segments、splits
    cache.py              # config_hash(cfg)、cache_dir(cfg)、is_fresh(cfg)、write/read
    stats.py              # FitStats、compute_fit_stats(frame)
    windows.py            # build_train_manifest、build_eval_manifest、context_batch、targets、segment_set
    labels.py             # resolve_threshold、future_event_labels
    profile.py            # build_meta(frame, cfg) -> dict
    types.py              # PreparedFrame、ContextBatch、SegmentSet 数据类
```

`PreparedFrame` 是一个冻结数据类：`frame: pl.DataFrame`、`channels: list[str]`、`freq: timedelta`、`meta: dict`。

## 2. 读取（`source.py`）

- CSV：`pl.read_csv(path, schema_overrides={ch: pl.Float64 for ch in channels}, try_parse_dates=False, encoding=...)`，再按 `time_format` 或 ISO 解析时间列。显式配置的通道必须转换为 Float64，转换失败时报配置错误。
- `channels` 为 null 时遵循父设计 3.1：只选择数值列，角色为 `target`。CSV 自动识别检查完整列的非空值能否转换为 Float64，避免前 N 行为空导致误判；字符串标识列不作为通道。全空列按可空浮点通道保留。Parquet 使用数值列或全空列，排除时间列。选择后统一输出 Float64，缺失保留 null。
- 自动识别用合成数据验证：数值列、前 N 行为空的数值列、全空列、字符串标识列并存时，输出只含数值和全空通道；显式配置的非法数值通道必须报错，错误信息不得包含原始值。
- 读取后按时间排序，检查单调；`dedup` 用 `unique(subset=time, keep=...)`。
- 只保留时间列与 `role != ignore` 的通道。

## 3. 重采样（`prepare.py`）

```python
frame.group_by_dynamic("time", every=freq, closed="right", label="right")
     .agg([pl.col(ch).mean() for ch in channels] + [pl.len().alias("_n")])
```

`aggregation: last` 时用 `.last()`。之后用 `pl.datetime_range(start, end, freq)` 生成完整网格左连接，`observed = _n > 0`。`freq == native_freq` 时先把时间戳向上取整到网格，再按同一逻辑补齐。

## 4. 分段算法

输入：`eligible` 布尔序列（网格顺序）。

1. 找出所有 `eligible == True` 的行号。
2. 相邻有效行号差值减 1 为中断长度（行数）；中断长度 × freq > `max_gap` 时断开。
3. 每段从首个有效行到末个有效行（含中间短中断行）。
4. 段时长 < `min_length` 的段丢弃（`segment_id = -1`）。
5. 剩余段按时间顺序编号 0..K-1。

用 numpy 在行号数组上向量化实现。

## 5. 划分算法

1. 取 `eligible` 行的累计计数 `c`，总数 N。
2. 对比例累计值 `r1 = 0.70, r2 = 0.80, r3 = 0.90`，边界行为首个 `c >= ceil(r_k × N)` 的有效行。
3. 边界时间 `b_k` 为该行时间。`time < b1` 为 fit，`b1 <= time < b2` 为 val，依此类推。
4. 边界写入 `meta.json`。

## 6. 窗口

行号即数组下标。设 `seg = segment_id`、`sp = split` 的 numpy 数组。

- 起点 o 合法的必要条件：`o - L + 1 >= 0`、`o + H < n`、`seg[o-L+1] == seg[o+H] != -1`（段为连续区间，首尾同段即全段同段）。
- 训练：另需 `sp[o+1] == fit` 且 `sp[o+H] == fit`（划分按时间单调，首尾同划分即全部同划分）。
- 评价（划分 s）：另需 `sp[o+1] == s` 且 `sp[o+H] == s`。
- 步长：在合法起点中按 `origin_row % stride == 0` 过滤，保证不同运行得到同一起点集合。
- 最大数量：`max_eval_origins` 非空时用 `np.linspace` 在合法起点序列上等距取整。

`context_batch(prepared, origin_rows, L)` 用 `np.lib.stride_tricks.sliding_window_view` 或花式索引取 `(B, C, L)`；`targets(prepared, origin_rows, H)` 返回 `(values, mask)`，mask 为非 null。

`segment_set(prepared, split)`：对每个段取 `split == split` 的行区间，得到 `(C, T_i)` 数组；长度小于 `min_rows` 的片段丢弃（由调用方传入 `L + H`）。

## 7. 标签（`labels.py`）

- `resolve_threshold(prepared, spec) -> float | tuple[float, float]`：`quantile` 用拟合段有效行的通道值计算（忽略 null）。
- `future_event_labels(prepared, origin_rows, rule, threshold) -> np.ndarray[int8]`：对每个起点取 `[o+1, o+W]`，条件满足为 1，null 为 0；用长度为 `min_duration` 的滑动求和判断是否存在连续满足段。窗口的合法性沿用第 6 节（以 W 代替 H）。

## 8. 缓存

- `config_hash`：对 `DatasetConfig` 中影响 PreparedFrame 的字段（source、native_freq、freq、aggregation、dedup、channels 的名称与角色、eligibility、segments、split）做 `model_dump_json` 后取 SHA-256 前 12 位。通道的 `unit`、`description` 不参与。
- `meta.json` 记录源文件大小与 `mtime_ns`；`is_fresh` 比较这两项与哈希。
- 写入先写临时文件再重命名。

## 9. CLI

```text
tsllm data list                 # id、源路径、是否已入库、缓存哈希
tsllm data ingest <id> [--force]
tsllm data profile <id>         # 行数、有效点、段数、划分边界、各通道空值率
```

`ingest` 的实现函数 `ingest_dataset(cfg: DatasetConfig, reporter: Reporter) -> PreparedFrame` 放在 `tsllm/data/prepare.py`，供后续 worker 复用。CLI 传入 `PrintReporter`。

## 10. 测试夹具

`tests/conftest.py` 提供 `make_synthetic_csv(tmp_path, ...)`：

- 3 个通道，10 s 采样，3 天。
- 第 1 个通道前 2,000 行为空（触发类型推断问题）。
- 第 2 天中间 4 h 停机（规则通道低于阈值）。
- 1 处 30 min 无记录断点；2 处 90 s 无记录断点。
- 3 个重复时间戳。
- 返回路径与对应的 `DatasetConfig`。

## 11. 性能预期

690 万行 × 19 列 CSV 读取约 1 GB 内存。重采样在 DataFrame 上一次完成。不做流式处理；若本机内存不足再改为 `scan_csv` + `collect(engine="streaming")`，并在任务备注中记录。
