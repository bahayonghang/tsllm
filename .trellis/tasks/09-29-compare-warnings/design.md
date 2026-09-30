# 对比警告设计

## 1. 边界

共享契约沿用 .trellis/tasks/archive/2026-09/09-28-tsfm-platform/design.md 第 1、6、7 节。本任务只扩展警告，增量契约记录于本任务，不修改归档父任务。

| 层 | 责任 | 文件 |
| --- | --- | --- |
| 比较 | 按作业种类产生警告及上下文，保留结果 | src/tsllm/runs/compare.py |
| HTTP 模型 | 声明可选上下文 | src/tsllm/service/models.py |
| 路由 | 保持校验、去重、下层调用，预计无需修改 | src/tsllm/service/routes/compare.py |
| 类型 | 服务导出 OpenAPI，再生成 TypeScript | web/openapi.json；web/src/api/schema.d.ts |
| 展示 | 按码中文化并关联运行/划分 | web/src/pages/ComparePage.tsx；局部提示组件或格式化函数 |
| 验证 | 合成接口、页面和浏览器用例 | tests/service/test_api_compare.py；web/tests/pages/ComparePage.test.tsx 等必要文件 |

前端不重新判定可比性，保留全部服务警告。

## 2. 增量响应契约

CompareWarningOut 保留必填 code: str、message: str，增加以下字段，均有英文 Field(description=...)：

| 字段 | 类型及默认值 | 含义 |
| --- | --- | --- |
| run_id | str 或 None，默认 None | 单运行状态或无实验指标警告的运行 ID |
| split | str 或 None，默认 None | 起点差异对应的划分 |

不适用字段可以为 null，旧响应可以省略。前端兼容两种形状。状态由 columns 按 run_id 获取，不重复新增状态字段。

| 码 | 条件 | 上下文 | 中文主要说明 |
| --- | --- | --- | --- |
| RUN_NOT_SUCCEEDED | 既有状态规则 | run_id | 运行尚未成功，当前结果可能不完整；附 ID/名称及状态 |
| DATASET_MISMATCH | 既有数据集规则 | 无 | 所选运行使用了不同的数据集 |
| TASK_MISMATCH | 既有任务类型规则 | 无 | 所选运行的任务类型不同 |
| CONTEXT_LENGTH_MISMATCH | 既有上下文长度规则 | 无 | 所选运行的上下文长度不同 |
| HORIZON_MISMATCH | 既有预测步长规则 | 无 | 所选运行的预测步长不同 |
| ORIGIN_SET_MISMATCH | 既有同划分起点哈希规则 | split | 对应划分的评价起点集合不同 |
| NON_EXPERIMENT_RUN | JobSpec.kind 为 ingest | run_id | 入库作业没有实验指标；结果保留该作业，指标显示为空 |

六类既有英文 message 不变。新增 message 使用英文并包含运行 ID，不包含原始数据值。

## 3. 比较逻辑

1. 沿用路由按输入顺序去重 ID。
2. 读取 JobSpec 时按 kind 收集入库 ID，不按名称或缺少指标推断种类。
3. 保持 columns、rows、null 填充及原有六类判定。
4. 为状态与起点警告附加 run_id/split。
5. 在既有警告后按去重输入顺序追加每个入库的 NON_EXPERIMENT_RUN，保持原警告相对顺序。
6. 返回 200；保留全部列，不造指标，全入库 rows 为空。

未成功入库同时有状态及无指标警告。其他既有差异继续提示，不扩大为通用缺失指标诊断。

## 4. 展示与兼容

- 使用局部码映射，沿用现有 ErrorAlert 的映射习惯，不引入国际化依赖。
- run_id 关联 columns 的名称和状态，可复用 StateTag。关联缺失时保留 ID 及原消息，不错误关联。
- split 保留原标识，例如“test 划分”，不解析英文句子。
- 已知码且上下文完整：中文主要说明加可辨认上下文；原始码和消息可作为次要详情。
- 旧响应、上下文缺失或关联列不可用：通用中文说明加原 message。
- 未知码：中文通用提示加原 code/message，不隐藏。
- 同码多条逐条显示。React key 结合上下文，并区分完全相同的条目，不以 code 为唯一 key。
- 按文本渲染，不引入 HTML；指标表、图表及选择规则不变。

旧前端可以忽略新增字段，新前端支持旧响应。仓库外严格响应校验客户端未验证，不宣称全部客户端兼容。

## 5. 取舍

| 选择 | 理由与代价 |
| --- | --- |
| 200 加结果与警告 | 用户已确认；调用方仍需处理警告 |
| 前端按码中文化 | 服务消息保持可用，需可选上下文支持动态信息 |
| 两个明确字段 | 满足当前需要，不引入任意 params 或全站翻译框架 |
| 保留原消息 | 支持旧版及降级，次要详情可能含英文 |
| 保持选择限制 | 常规操作排除入库，服务覆盖手工链接及 API |

## 6. 验证

接口用临时 RunStore 和合成 DatasetConfig/JobSpec。入库夹具不写 metrics.json，不复用当前总会写预测指标的 _finished。不得执行真实入库、训练或下载。

页面在 fetch 层提供英文响应，覆盖全部码、旧响应、未知码、缺少上下文、同码多条、空指标和 URL 直达。沿用路由及辅助函数，不 mock 业务 hooks。

浏览器使用生产构建和 9000，三个服务根目录指向独立临时夹具，只含合成终态作业，防止启动恢复真实运行。可见窗口检查 390 px、1280 px，截图不写仓库。

## 7. 风险与回退

- 动态信息丢失：结构化上下文及多运行/划分用例。
- 类型漂移：生成文件同次更新，连续生成字节比较。
- 未知码/旧响应丢失：保留消息并测试降级。
- 服务恢复真实运行：启动前核对临时根目录、终态夹具及端口。
- 范围扩张：差异仅接受本任务必要文件。
- 无数据迁移。回退同时恢复比较逻辑、响应模型、页面和生成文件并重建前端，不回退其他任务或私有目录；提交后 Git revert 另需授权。
