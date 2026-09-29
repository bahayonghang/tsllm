# Research: 本地模型库接口审计

- Query: 核对 TimesFM 2.5、TTM、Chronos-2 的实际调用、检查点解析、微调和表示接口。
- Scope: mixed；本地已安装源码为 API 依据，模型卡为许可依据。仅写本文件。
- Date: 2026-09-29

## Findings

### 环境与依据

本地 `importlib.metadata.version` 确认 torch `2.11.0+cu128`、transformers `5.17.0`、peft `0.21.0`、chronos-forecasting `2.3.2`、granite-tsfm `0.3.9`。本审计不下载权重、不运行 GPU 或训练。已执行的小模型操作仅限 CPU 随机初始化和前向调用，不代表 AC4–AC7 通过。

关联规范：父任务 `design.md:200–247`；本任务 `design.md:90–121`；`.trellis/spec/backend/model-adapter-guidelines.md:82–125`。已批准的 Reporter 与 mode 参数已在父子设计中同步。

以下源码路径均相对 `.venv/Lib/site-packages/`，完整路径和行号可直接复查。

### TimesFM 2.5：已核实

| 文件 | 用途 |
| --- | --- |
| `transformers/models/timesfm2_5/configuration_timesfm2_5.py` | 官方随机模型配置；默认 patch=32、horizon=128、9 个分位数。 |
| `transformers/models/timesfm2_5/modeling_timesfm2_5.py` | 前向、归一化、输出、损失、隐藏层和 LoRA 线性层。 |

- 注意力层后缀为 `q_proj`、`k_proj`、`v_proj`、`o_proj`（`modeling_timesfm2_5.py:280–290`）；MLP 后缀为 `fc1`、`fc2`（`:84–85`）。CPU 随机模型 `named_modules()` 确认路径为 `model.layers.0.self_attn.*` 与 `model.layers.0.mlp.*`。
- `forward(past_values=[一维张量], forecast_context_len=..., future_values=二维目标)` 返回 `mean_predictions`、`full_predictions`、`last_hidden_state`、`loss`（`:737–854`）。默认输出分别为 `(N,H)`、`(N,H,10)`、`(N,P,D)`。
- `full_predictions` 的第 0 列是额外点预测通道；分位数使用 `[..., 1:]` 与 `config.quantiles` 配对。`mean_predictions` 取 `decode_index=5`，默认对应中位数（配置 `:78–84`，模型 `:658,802–816`）。
- 表示专用路径为 `prediction_model.model(past_values=二维输入, past_values_padding=掩码).last_hidden_state`（`:564–644`）；对 patch 维取平均。预测包装层也直接返回第一次解码的隐藏状态（`:848–854`）。
- 损失在标准化空间计算 MSE 加分位数损失，不屏蔽未来目标 NaN（`:830–846`）。训练目标需在适配器侧拒绝缺失项或选择完整窗口；不能把 NaN 直接传入该损失。
- dtype 不会在包装层自动转换：`_preprocess` 保留输入 dtype（`:693–707`），归一化结果直接进入 `input_ff_layer`（`:608–612`）。无 autocast 时须使输入 dtype 与线性权重一致。CPU 按项目协议用 fp32；CUDA bf16 的实际验收由实施代理执行。

已执行 CPU 随机配置：`patch_length=8, context_length=32, horizon_length=8, num_hidden_layers=1, hidden_size=32, intermediate_size=32, head_dim=16, num_attention_heads=2, num_key_value_heads=2, output_quantile_len=8, max_position_embeddings=32`。L=32 时输出为 mean `(1,8)`、full `(1,8,10)`、hidden `(1,4,32)`，预测和损失有限。未断言随机值的具体损失。

**子设计字面调用需要澄清**：`forecast_context_len=L` 并不自动补齐 patch 倍数。底层 `:582–583` 直接 reshape；`_preprocess` 只补到传入的 context 长度。CPU probe 在 patch=8、L=30 时首次失败：`RuntimeError: shape '[1, -1, 8]' is invalid for input of size 30`。L=32 复测通过。真实默认 patch=32 对 L=120 有同一结构约束。建议内部有效长度设为 `ceil(L / patch_length) * patch_length`，保留原始 L 个观测，交给库左填充与掩码；父契约的输入和输出形状不变。已通知主会话和实施代理，在决策前暂停该调用细节。

### TTM：已核实

| 文件 | 用途 |
| --- | --- |
| `tsfm_public/toolkit/get_model.py` | HF 模型系列识别、L/H 分支选择、本地加载。 |
| `tsfm_public/resources/model_paths_config/ttm.yaml` | 官方随包分支映射与可用 L/H 组合。 |
| `tsfm_public/models/tinytimemixer/configuration_tinytimemixer.py` | 小模型参数及预测长度校验。 |
| `tsfm_public/models/tinytimemixer/modeling_tinytimemixer.py` | 主干、解码器、预测头、输入边界和掩码损失。 |
| `transformers/utils/hub.py` | 本地目录优先于 revision 的文件解析证据。 |

#### 分支选择与本地快照

`get_model` 只根据 HF 名称前缀识别 r2（`get_model.py:59–76`），随后从随包 YAML 选择 L/H 组合（`:239–328,438–467`）。解析后的本地路径被识别为类型 0，不能继续进行同一分支选择。必须在下载前选择分支。

`return_model_key=True` 只运行选择逻辑，不下载模型（`:214–215,544–546`）。返回值是 YAML 的 key，不保证等于分支名。`ttm.yaml:15–20` 的 `512-96-r2` 对应 revision `main`。

已执行的离线选择调用结果：

| 请求 L/H | 返回 key | 真实分支 |
| --- | --- | --- |
| 32/8 | ValueError：最短上下文为 52 | 无 |
| 52/16 | `52-16-ft-r2.1` | 同 key |
| 90/8 | `90-30-ft-r2.1` | 同 key |
| 120/30 | `90-30-ft-r2.1` | 同 key |
| 512/8 | `512-48-ft-r2.1` | 同 key |
| 512/96 | `512-96-r2` | `main` |

**首次确定失败**：对已有本地目录调用 `get_model(local_path, context_length=512, prediction_length=8)`，在读取模型前产生 `TypeError: argument of type 'NoneType' is not iterable`。原因是 `:537–538` 保留 `ttm_model_revision=None`，`:557` 执行 `'-dec-' in ttm_model_revision`。

修正验证仅使用 mock：传入 `model_revision='explicit-local'` 后，调用到 `TinyTimeMixerForPrediction.from_pretrained(local_path, revision='explicit-local', prediction_filter_length=8)`，mock 模型返回成功。该结果证明参数传递修正；没有验证真实本地权重加载。主会话已将该修正归类为子任务内部库调用调整。

建议调用顺序：

1. HF id 且用户未固定 revision：首次得到 L/H 后用 `get_model(repo_id, ..., return_model_key=True)` 选择 key。
2. 通过 `importlib.resources.files('tsfm_public.resources.model_paths_config').joinpath('ttm.yaml').read_text(encoding='utf-8')` 读取对应 `revision`。调用公共 `get_model` 选择，不复制选择算法。
3. 用所选分支调用项目 `resolve_checkpoint`，保留本地快照路径和实际 commit。
4. 调用 `get_model(str(snapshot_path), ..., model_revision=resolved_commit)`。
5. 显式用户 revision 不重新自动选分支。纯本地目录的未知 revision 仍记录未知；仅向库传非空占位符避免 None 异常。

本地占位符不会选中其他文件：`transformers/utils/hub.py:391–405` 对本地目录直接拼接文件名并返回，执行点早于 Hub 的 revision 解析。不要把库调用占位符写入 `resolved_checkpoint.revision`。

#### L/H、参数冻结与 NaN

- TTM 模型自身会将过长上下文裁为最后 `config.context_length` 步，也会对过短上下文左补零（`modeling_tinytimemixer.py:3453–3471`）；掩码做同样操作（`:3476–3491`）。因此 120/30 选中 native L=90 后，模型实际使用最后 90 步。适配器无需添加裁剪，应通过 Reporter 明确记录请求长度和有效长度。
- `force_return=None` 保持找不到分支时抛错；不得使用随机模型、递归预测或零填充选型作为静默回退。固定或本地检查点的 `prediction_filter_length` 必须满足 `0 < H <= config.prediction_length`（配置 `:420–422`）。可用组合以随包 YAML 为准。
- 参数边界是 `model.backbone`、`model.decoder`、`model.head`（模型 `:3380–3389`）。按已批准子设计冻结 `.backbone`，保留 decoder 与 head 可训练。冻结属性不等于设置全部模型为 eval；训练与验证模式仍由训练循环控制。
- `past_values` 为 `(B,L,C)`，预测 `prediction_outputs` 为 `(B,H,C)`（`:3448–3450,3663–3667`）。
- `past_observed_mask`/`future_observed_mask` 标记已经把缺失值替换为零后的可观测项（`:3417–3436`）。预测上下文仍应先遵守子设计的 FitStats 标准化、前填充、后填充、零填补。
- 点预测损失只在显式提供 `future_observed_mask` 时选择观测目标，否则直接用所有目标计算 MSE（`:3627–3633`）。全空目标会形成空张量均值，需在抽样层排除。
- 官方 main 检查点配置的 `scaling='std'`。外部 FitStats 缩放与内部 checkpoint scaler 是两个层次，不应未经设计决定修改预训练配置。
- 随机小模型配置入口支持 `context_length, prediction_length, patch_length, patch_stride, d_model, num_layers, decoder_num_layers, decoder_d_model, dropout, head_dropout`（配置 `:159–211`）。`patch_stride` 必须等于 `patch_length`（`:391–392`）。本审计未构建 TTM 小模型。

### Chronos-2：已核实

| 文件 | 用途 |
| --- | --- |
| `chronos/chronos2/pipeline.py` | fit、predict、embed、保存和重载。 |
| `chronos/chronos2/config.py` | `Chronos2CoreConfig` 和 `Chronos2ForecastingConfig`。 |
| `chronos/chronos2/model.py` | patch/token 顺序、归一化和 NaN 掩码损失。 |
| `peft/mapping_func.py`、`peft/auto.py` | 基础检查点引用及 adapter 重载。 |

#### fit、LoRA 与保存

- `fit` 复制 config，新建 `Chronos2Model` 并复制权重；不修改原 pipeline（`pipeline.py:200–225`）。函数返回新的 pipeline（`:365,382`），LoRA 模式的返回模型仍是 PEFT 包装模型。
- 模式为 full 时必须传 `lora_config=None`，非空会抛 ValueError（`:195–198`）。模式为 lora 时预先确认 peft 可导入，避免库内部回退 full（`:181–189`）。
- `LoraSpec` 转换字段为 `r`、`lora_alpha`、`lora_dropout`、`target_modules`；不能原样传 `alpha`、`dropout`。默认 targets 从已安装源码明确为 `self_attention.q/v/k/o` 和 `output_patch_embedding.output_layer`（`:207–219`）。自定义目标为 None 时使用该明确列表，避免由通用 PEFT 映射猜测。
- Trainer 覆盖参数直接传给 `fit` 的 `**extra_trainer_kwargs`（`:123,319`），不传一个名为 `extra_trainer_kwargs` 的字典。`dataloader_num_workers=0` 已是默认；可显式传 `max_grad_norm`、`logging_steps`、有验证时一致的 `eval_steps/save_steps`。
- 拷贝新模型时只移动 device，没有复制加载 dtype（`:202–203`）。Trainer 默认在 CUDA sm>=80 打开 bf16（`:254–282`）；为严格遵守 BackboneConfig，应显式传配置对应的 `bf16`。返回模型的实际 dtype 需由实施测试核验。
- 最终保存目录为 `output_dir / finetuned_ckpt_name`，默认名称 `finetuned-ckpt`（`:119,368–369`）。只有显式传该参数才会使用其他目录名。`save_pretrained` 直接委托底层模型（`:1193–1197`）：full 保存全模型，LoRA 保存 PEFT adapter。复制该最终目录即可满足子设计保存流程。
- `Chronos2Pipeline.from_pretrained(adapter_dir)` 调用 `AutoPeftModel.from_pretrained`，然后 `merge_and_unload()`（`:1172–1177`）。重载后没有原来的可训练 LoRA 包装，LoRA 参数比例应在重载前记录。
- Adapter 重载依赖 `adapter_config.json` 的 `base_model_name_or_path`（`peft/auto.py:113–156`）。从随机 config 直接构造的模型 `name_or_path` 为空，PEFT 转为 None（`peft/mapping_func.py:140–142`）。离线往返测试应先把随机基础模型保存到测试临时目录并从该路径加载，再执行 fit。真实下载快照路径应保持可用。

#### embed、NaN 与随机小模型

- `embed` 返回二元组 `(embeddings, loc_scale)`；第一个对象是按输入分组的张量列表（`pipeline.py:1067–1094,1130–1144`）。
- token 顺序为 context patches、可选 REG、future patch（`model.py:598–623`）。官方配置 `use_reg_token=True`，因此 L32/patch8 得到 P+2=6 个 token。按子设计移除最后一个 future token，保留 REG，再对 patch/token 维求平均。
- NaN 上下文通过原生 mask 处理，先 fp32 归一化，再转模型 dtype（`model.py:393–417`）。未来 NaN 也由原生 loss mask 处理（`:531–565`），与 TimesFM 的目标处理不同。
- 已执行 CPU 随机配置：`d_model=32, d_kv=8, d_ff=64, num_layers=1, num_heads=4, dropout_rate=0, architectures=['Chronos2Model']`；`chronos_config={context_length:32, input_patch_size:8, input_patch_stride:8, output_patch_size:8, quantiles:[0.1,...,0.9], use_reg_token:True, max_output_patches:2}`。预测输入 B2/C2/L32、H8，含一个 NaN；返回两个 `(2,9,8)` 张量且预测有限。embed 返回两个 `(2,6,32)` 张量。
- 首次小模型使用 `[0.1,0.5,0.9]` 分位数，predict 抛 `ValueError: Unrolled quantiles must be a subset of the model's quantiles`。原因是默认 `unrolled_quantiles` 为 0.1 至 0.9 全部九项，即使短预测也先校验（`pipeline.py:578–595`）。改为九项后通过；属于测试配置修正。没有理由将全部 Chronos 小模型测试移入 weights。

### 模型卡许可与 revision：已核实元数据

通过 `hf-mirror.com` 读取官方仓库 API 元数据，并按得到的 commit 读取 `README.md` 与 `config.json`。三个 main 模型卡的第 2 行均为 `license: apache-2.0`；注册值可规范为 `Apache-2.0`。以下只代表查询时的分支解析，实际验收须记录真正加载的 commit。

| 官方仓库 | 查询分支 | commit |
| --- | --- | --- |
| `amazon/chronos-2` | main | `29ec3766d36d6f73f0696f85560a422f50e8498c` |
| `google/timesfm-2.5-200m-transformers` | main | `5a9806b9b291fad9233b5249d88263f1846304d3` |
| `ibm-granite/granite-timeseries-ttm-r2` | main | `d6a79570cac0f33d526601cd3a0fc7c80a8f9a2f` |
| `ibm-granite/granite-timeseries-ttm-r2` | 52-16-ft-r2.1 | `8c9c1d742ec5893d6419e3aa2ab21ed23e28df85` |
| `ibm-granite/granite-timeseries-ttm-r2` | 90-30-ft-r2.1 | `6e5cb8ee51e0634a45637490f5db43148b2fa6be` |

外部原始来源（本轮读取其镜像，不下载权重）：

- `https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/README.md`
- `https://huggingface.co/google/timesfm-2.5-200m-transformers/blob/5a9806b9b291fad9233b5249d88263f1846304d3/README.md`
- `https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2/blob/d6a79570cac0f33d526601cd3a0fc7c80a8f9a2f/README.md`
- `https://hf-mirror.com/api/models/<repo_id>/revision/<branch>`：元数据包含 sha 和 cardData.license；两个 r2.1 分支也返回 apache-2.0。

实际 main 配置摘要：Chronos context8192/patch16/max_output_patches64/21 个分位数；TimesFM context16384/patch32/horizon128；TTM context512/patch64/horizon96/decoder启用/scaling=std。该摘要用于选择真实验收输入，不代替加载实测。

## Caveats / Not Found

- 本文件为接口研究记录，不是验收通过记录。真实权重、GPU、5 步微调、损失下降和保存往返尚未由本审计执行。
- TimesFM 内置 loss 的分位数索引值得保留为库语义限制：`modeling_timesfm2_5.py:839–843` 排除 `decode_index=5` 后，将列 `[0,1,2,3,4,6,7,8,9]` 传给按 config.quantiles 顺序配对的 `_quantile_loss`（`:727–733`）。输出分位数映射却是列 `1..9`。本审计未修改该库损失，也未把该源码差异写成训练失败；子设计要求直接使用内置 loss，改变损失定义需另行决定。已向主会话报告。
- 未读取 `data/` 或 `ref/`；未修改源码、测试、共享契约、spec 或 Git 状态。
- `CONTEXT.md` 不存在。记忆索引的定向搜索没有相关结果，结论来自当前文件。
