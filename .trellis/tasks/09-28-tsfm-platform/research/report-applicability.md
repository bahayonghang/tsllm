# 研究报告条款与本数据的对应

来源：`ref/cement_tsfm_research_20260928/industrial_tsfm_cement_report.md` 与 `cement_finetune_blueprint.yaml`（`ref/` 在 `.gitignore` 中）。报告性质为研究方案，未在用户数据上训练。

## 直接采用

| 报告条款 | 位置 | 在本平台的落点 |
|---|---|---|
| 按原始时间先划分拟合 / 验证 / 校准 / 测试，比例 0.70 / 0.10 / 0.10 / 0.10 | 9.1、blueprint `split` | data-contract：`splits.py` |
| 禁止先生成全部窗口再随机拆分；拟合段内可随机抽窗 | 9.1、6.2 | data-contract：窗口清单按段生成 |
| 训练窗口目标必须位于拟合段；评价起点可使用更早的合法历史 | 9.1 | data-contract：泄漏检查 |
| 不跨长缺失或停窑拼窗 | 5.2、6.2 | data-contract：运行段切分 |
| 预处理统计只用拟合段 | 4.3、8.4 | data-contract：`FitStats` |
| 输入掩码与目标掩码分开维护 | 5.2 | data-contract：窗口批次结构 |
| 遵循各基座自身归一化（TimesFM / Chronos 输入原始值，TTM 外部缩放） | 8.4 | backbone-adapters |
| Chronos-2 LoRA 必须确认 peft 生效；`fit()` 返回新 pipeline；推理 `cross_learning=False` | 8.2、8.3 | backbone-adapters |
| 基线：保持值、线性；TTM 作成本对照 | 9.2 B0、S1 | backbone-adapters |
| 首轮 120 min 历史、30 min 预测，按 5 / 15 / 30 min 提前量评价 | 6.1、9.3 | experiment-runner 默认配置 |
| 过程指标用物理单位 MAE / RMSE，另报拟合段尺度归一化宏平均 | 9.3 | experiment-runner：`metrics.py` |
| 概率输出报分位数损失、覆盖率、区间宽度 | 7.3、9.3 | experiment-runner |
| 资源指标：峰值显存、p50 / p95 时延、加载时间 | 9.3 | experiment-runner |
| 尾部阈值用拟合段规则定义 | 9.3 | experiment-runner：分类标签规则 `quantile` 阈值 |
| 记录权重 revision、许可、CUDA、transformers、peft 版本 | 8.5 | experiment-runner：运行环境快照 |
| 初筛 3 个随机种子 | 9.3 | experiment-runner：种子字段，多种子由多次运行组成 |

## 本数据无法执行

| 报告条款 | 原因 |
|---|---|
| 真实化验锚点质量损失、OAM-Net 质量映射、F3 / C2 实验 | 无 f-CaO 标签 |
| IM / SM / KH 低频条件、年龄与发布延迟特征 | 无生料化验数据 |
| `sample_time` / `available_time` 双时间字段 | 仅有 DCS 时间戳；DCS 数据视为 `available_time = sample_time` |
| 33 通道配置 | 本数据 18 通道 |

平台保留"外部稀疏标签"的扩展位置（按时间戳关联、含可用时刻），本轮不实现。

## 本轮不做

- TimesFM 2.5 多变量残差适配器（报告 6.3 的 F2）：先完成 LoRA 与零样本对照，适配器另立任务。
- 独立校准段上的区间校准：校准段在划分中保留，校准算法另立任务。
- 统计显著性重采样、标签比例学习曲线、消融矩阵。
- 厂内服务化与影子模式（报告 11 节）。
