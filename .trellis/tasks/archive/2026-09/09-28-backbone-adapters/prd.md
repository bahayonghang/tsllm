# 基座模型适配层与基线

父任务：`.trellis/tasks/09-28-tsfm-platform/`。共享契约见父任务 `design.md` 第 3.2（`backbone`、`finetune` 段）与第 5 节。

## 目标

建立统一的基座适配器接口与注册表，实现 6 个适配器，使任务层可以不区分具体模型完成预测、微调与表示提取。

## 依赖

- `09-28-data-contract` 已归档：使用其 `ContextBatch`、`SegmentSet`、`FitStats`、`Reporter`。

## 需求

- R1 依赖：`torch==2.11.*`（Windows / Linux 从 `https://download.pytorch.org/whl/cu128` 安装）、`transformers>=5.17,<6`、`peft>=0.21,<1`、`chronos-forecasting>=2.3.2,<3`、`granite-tsfm>=0.3.9,<0.4`、`scikit-learn<1.8`、`huggingface-hub`；提交 `uv.lock`。
- R2 `tsllm.config.backbone`：`BackboneConfig`、`FinetuneConfig`、`LoraSpec`（父设计 3.2）。
- R3 `tsllm.backbones.base`：`Capabilities`、`ForecastOutput`、`Backbone` 基类（未实现的方法抛 `CapabilityError`）、`BackboneLoadError`。
- R4 注册表：`register_backbone`、`get_backbone(name)`、`list_backbones()`；列出注册信息时不导入 torch 与任何模型库。注册信息含能力、Options schema、依赖是否已安装、许可名称与链接。
- R5 检查点解析：`checkpoint` 为 HF 名称时用 `huggingface_hub.snapshot_download` 解析到本地快照目录并得到 commit；为本地目录时直接使用。遵循 `HF_ENDPOINT` 与 `HF_HUB_OFFLINE`。解析结果（本地路径、revision）由适配器属性 `resolved_checkpoint` 暴露。
- R6 适配器（能力见父设计第 5 节表格）：
  - `persistence`
  - `ridge`：`finetune()` 用 `SegmentSet` 生成训练窗口，按 FitStats 标准化，sklearn `Ridge`
  - `features`：`embed()` 输出每通道 6 个统计量，NaN 安全
  - `chronos2`：零样本、LoRA、full 微调与表示提取；LoRA 前检查 peft 可导入，缺失时抛错，不允许回退为 full
  - `timesfm25`：零样本、LoRA 微调（自写训练循环）与表示提取；通道独立
  - `ttm`：零样本与 head 微调；外部标准化使用 FitStats
- R7 每个适配器在 docstring 中写明 NaN 处理方式与归一化方式。
- R8 `dtype: bf16` 仅在 CUDA 上生效；`device: cpu` 时强制 fp32。
- R9 适配权重保存与加载：`save_adapter(path)` / `load_adapter(path)` 往返后预测结果一致。

## 验收标准

- [x] AC1 `uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest` 全部通过，默认测试不联网、不需要权重、不需要 GPU。
- [x] AC2 测试 `list_backbones()` 返回 6 项，调用前后 `sys.modules` 中不出现 `torch`、`chronos`、`transformers`、`tsfm_public`。
- [x] AC3 `persistence`、`ridge`、`features` 有数值正确性测试（含 NaN 输入）。
- [x] AC4 `timesfm25`、`ttm` 用库自带配置类构建的随机初始化小模型测试：输出形状、NaN 输入不产生 NaN 输出、微调若干步后训练损失下降、适配权重往返一致。`chronos2` 若无法离线构建小模型，其同类测试标记为 `weights`。
- [x] AC5 标记 `weights` 的冒烟测试：3 个真实检查点各完成一次加载、零样本预测和 5 步微调（`ttm` 为 head，其余为 lora），并断言 LoRA 可训练参数数量大于 0 且小于总参数的 5%。在配置镜像或本地权重后于本机执行一次，结果与 revision 写入任务备注。
- [x] AC6 标记 `gpu` 的测试：`chronos2` 与 `timesfm25` 在 CUDA + bf16 下完成零样本预测。在本机执行一次，结果写入任务备注。
- [x] AC7 `torch.cuda.is_available()` 在本机 `uv run` 环境中为 True，`torch.cuda.get_device_capability()` 为 (12, 0)，写入任务备注。

## 实施备注

- AC7 已执行：`uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"`，退出码 0，耗时 9.01 s，输出 `2.11.0+cu128 True (12, 0)`。
- 环境：Python 3.13.11、CUDA runtime 12.8、RTX 5090 Laptop GPU、驱动 617.14、总显存 24,463 MiB；bf16 支持检查为 True。该检查未运行模型，不代表 AC5 或 AC6 通过。
- 首次依赖安装中断及成功重试分别保留在 `research/dependency-validation.md`。安装重试耗时 533.08 s，退出码 0。
- 用户已批准共享协议修正：`load(..., *, reporter)`、`finetune(..., *, mode)`。具体依据和同步范围见 `research/contract-adjustments.md`。

- 步骤 7 修正后四项门禁全部通过：Ruff check/format、Pyright 均退出 0；离线 pytest 125 passed、5 deselected、2 warnings，11.97 s。最终全范围独立审查已通过，最终 pytest 为 125 passed、5 deselected、2 warnings，12.30 s；报告为 research/final-review.md。
- AC5：Chronos2 和 TimesFM25 均完成真实 LoRA 5 步，可训练参数比例分别为 1.000055% 和 1.051394%；TTM 使用 head，准确 5 步。
- AC6：Chronos2 与 TimesFM25 的真实 CUDA bf16 预测通过。AC5/AC6 的实际 revision、加载/训练耗时、峰值显存见 verification.md 和 research/real-acceptance.md。
- 首轮真实命令为 4 passed、1 failed；TTM 的频率 token 缺失修正后，同一分支/commit 的定向复测为 1 passed。首轮失败证据保留，不以跳过或改检查点完成验收。
