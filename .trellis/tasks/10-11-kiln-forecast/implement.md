# 阳泉回转窑时序预测执行计划

开始条件：`prd.md`、`design.md` 和本文件已确认，并且 `task.py start` 已把状态改为 `in_progress`。在此之前不入库、不跑模型。

## 步骤

1. 确认源文件。
   - 记录 `data/阳泉回转窑联合训练孪生样本/data_in.csv` 的字节数和 mtime。
   - 文件不存在则停止。
2. 入库并画像。
   - `uv run tsllm data ingest yangquan_kiln`
   - `uv run tsllm data profile yangquan_kiln`
   - 把输出写入 `research/ingest.md`，包括缓存哈希、有效点数、段数和四个划分边界。
   - 与 523,702 个有效分钟比较。偏差超过 ±2% 时只记录源指纹，不改规则。
3. CPU 基线，锁定起点清单。
   - `uv run tsllm run configs/runs/kiln_persistence.yaml`
   - `uv run tsllm run configs/runs/kiln_ridge.yaml`
   - 读取两个运行的 val/test `n_origins` 与 `origin_set_hash`。
   - 源文件字节数仍为 1,068,005,224 时，核对 val `e51e301e6b09`、test `07c9ced03282`。
   - 两个基线的哈希必须相同。否则停止，不进入 GPU。
4. 零样本。每条命令都带镜像：
   - `HF_ENDPOINT=https://hf-mirror.com uv run tsllm run configs/runs/kiln_chronos2_zero_shot.yaml`
   - `HF_ENDPOINT=https://hf-mirror.com uv run tsllm run configs/runs/kiln_timesfm25_zero_shot.yaml`
   - `HF_ENDPOINT=https://hf-mirror.com uv run tsllm run configs/runs/kiln_ttm_zero_shot.yaml`
   - 每个运行结束后立刻核对起点哈希和 `env.json` 的 revision。不一致则停止。
5. LoRA。仍串行，仍带镜像：
   - `HF_ENDPOINT=https://hf-mirror.com uv run tsllm run configs/runs/kiln_chronos2_lora.yaml`
   - `HF_ENDPOINT=https://hf-mirror.com uv run tsllm run configs/runs/kiln_timesfm25_lora.yaml`
   - 确认 `runs/<run_id>/adapter/` 存在，且训练只用 fit 段。
6. 写 `research/comparison.md`。
   - 七行：`run_id`、基座、模式、状态、revision、val/test 的 `mae_norm_macro`、`rmse_norm_macro`、`n_origins`、`origin_set_hash`、`load_seconds`、`train_seconds`、`peak_vram_mb`。
   - 按 val `mae_norm_macro` 升序排列。
   - 写明 test 未用于选型。
   - 抄录 warning 和 TTM 的 `effective_context_length`。
7. 代码审查。
   - 没有产品代码改动时，说明 diff 为空。
   - 有 R7 修复时，对改动范围运行 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest`。不把真实权重放进默认测试。

## 验证命令

```bash
uv run tsllm data profile yangquan_kiln
uv run tsllm runs list
uv run tsllm runs show <run_id>
```

七个 `runs show` 的同一划分 `origin_set_hash` 必须一致。需要权重的六个运行用 `env.json` 核对 AC5 的 revision。

## 审查门禁

- 步骤 2 之后：画像计数和源指纹已写入 `research/ingest.md`。
- 步骤 3 之后：CPU 基线哈希一致，才允许下载或加载权重。
- 步骤 4 之后：三个零样本 revision 和哈希通过，才允许开始 LoRA。
- 步骤 6 之后：对照 PRD 的 AC1–AC6。未满足不标记完成。

## 回滚

- 失败的 `runs/<run_id>/` 保留，不删除。
- 不通过修改 YAML 窗口或有效性规则回退到旧哈希。
- 若步骤 7 引入了错误修复，该修复单独提交；实验记录留在任务 `research/`，不把 `runs/` 或 `cache/` 加入提交。
