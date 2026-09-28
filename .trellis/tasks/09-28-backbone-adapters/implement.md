# 适配层执行计划

开始条件：`09-28-data-contract` 已归档。

## 步骤

1. 依赖
   - `pyproject.toml` 加入 R1 依赖；`[[tool.uv.index]] name = "pytorch-cu128"`、`url = "https://download.pytorch.org/whl/cu128"`、`explicit = true`；`[tool.uv.sources] torch = [{ index = "pytorch-cu128", marker = "sys_platform == 'win32' or sys_platform == 'linux'" }]`。
   - `uv lock`、`uv sync`。
   - 验证 AC7：`uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"`。
2. `config/backbone.py`、`backbones/base.py`、`registry.py`、`checkpoint.py`；测试注册表与无重型导入。
3. `persistence.py`、`ridge.py`、`features.py`、`windows.py`、`nan.py`；基线测试。
4. `timesfm25.py` + `training.py`（共享训练循环）；随机小模型测试。
5. `ttm.py`；随机小模型测试。
6. `chronos2.py`；小模型或 weights 测试。
7. weights 与 gpu 冒烟测试；在本机执行，结果写入 `prd.md` 备注（revision、耗时、显存）。

## 验证命令

```bash
uv sync
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest
HF_ENDPOINT=https://hf-mirror.com uv run pytest -m "weights or gpu"
```

## 审查门禁

- 步骤 2 完成后检查：`python -c "import tsllm.backbones; import sys; print('torch' in sys.modules)"` 输出 False。
- 步骤 6 完成后运行 `trellis-check`。

## 回滚点

- 步骤 1 的依赖变更单独提交，可独立回退。
- 每个模型适配器是独立文件；某个适配器验收失败时可从 `backbones/__init__.py` 移除注册并回退该文件，不影响其他适配器。
