# 共享适配器协议缺项：已批准修正

## 状态

主会话与独立 trellis-check 均确认以下两项缺失。用户随后回复“批准实施”，批准两项协议修正。父共享设计、适配层子设计、模型适配规范与 experiment-runner 的接口规划已同步；允许继续步骤 2–7。运行器只同步规划，不开始实施。下列行号保留预审时的定位。

## 证据与影响

| 缺项 | 证据 | 影响 |
| --- | --- | --- |
| 微调模式没有协议入口 | 父 `design.md:112` 将 `mode` 放在 RunConfig 顶层；`:221–224` 的 load/finetune 均没有 mode；子 `design.md` 第 2 节的 BackboneConfig 与 FinetuneConfig 也没有 mode；第 4.4 节要求按 mode 调用 Chronos fit | 调用方无法通过既定协议区分 Chronos 的 lora/full，也无法让适配器核验传入模式；自行固定默认模式会丢失用户配置 |
| load/embed 阶段没有 Reporter 入口 | 父 `design.md:221–224` 只有 finetune 接收 Reporter；子 `design.md:86` 要求 features.embed 对全 NaN 通道报告计数；规范还要求报告未指定 revision 的警告 | 分类流程只执行 load/embed，无法通过既定协议发送 features 警告；模型加载阶段也没有注入的 Reporter |

## 建议的最小共享修正

保持 RunConfig.mode 为唯一序列化模式字段；只新增显式方法参数：

```python
def load(
    self, cfg: BackboneConfig, fit_stats: FitStats | None, *, reporter: Reporter
) -> None: ...

def finetune(
    self, train: SegmentSet, val: SegmentSet | None, cfg: FinetuneConfig,
    context_length: int, horizon: int, reporter: Reporter,
    *, mode: Literal["lora", "head", "full"],
) -> None: ...
```

- 任务调用方将 `RunConfig.mode` 显式传给 `finetune(mode=...)`。适配器在训练前验证 `mode in forecast_modes`，不支持的模式抛 `CapabilityError`。Chronos 将所选模式原样传给 `pipeline.fit(finetune_mode=...)`。
- `load` 保存调用方注入的 Reporter，供加载警告和后续 `embed` 使用。`finetune` 继续接收其已有的 Reporter 参数。
- 不增加 BackboneConfig 或 FinetuneConfig 的 mode 字段；不改变 ContextBatch、SegmentSet、FitStats 或 Reporter 本身。

## 确认后的同步范围

1. 父任务 `design.md` 第 5 节协议和模式规则。
2. backbone-adapters 的 `design.md`、相关 PRD/implement 条目与测试要求。
3. `model-adapter-guidelines.md` 的协议、load 示例和警告要求；必要的 logging 指南说明。
4. experiment-runner `design.md` 第 4 节预测调用及第 6 节分类加载调用，只同步接口规划，不开始该任务实施。

## 修正后的验证要求

- 通过统一接口分别传入 lora/full，断言 Chronos 收到准确的 `finetune_mode`。
- 不支持的训练模式必须在参数更新前抛 `CapabilityError`。
- 捕获注入 Reporter，断言 features 的全 NaN 通道计数警告与缺失 revision 警告可达。
- 保持注册表无重型导入、数据接口和防泄漏测试有效；真实 LoRA 比例验收不变。
