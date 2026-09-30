import { Alert, Space, Typography } from "antd";
import type { Schemas } from "../api/client";
import { StateTag } from "./StateTag";

const LABELS = new Map<string, string>([
  ["RUN_NOT_SUCCEEDED", "运行尚未成功，当前结果可能不完整"],
  ["DATASET_MISMATCH", "所选运行使用了不同的数据集"],
  ["TASK_MISMATCH", "所选运行的任务类型不同"],
  ["CONTEXT_LENGTH_MISMATCH", "所选运行的上下文长度不同"],
  ["HORIZON_MISMATCH", "所选运行的预测步长不同"],
  ["ORIGIN_SET_MISMATCH", "运行的评价起点集合不同"],
  ["NON_EXPERIMENT_RUN", "入库作业没有实验指标；结果保留该作业，指标显示为空"],
]);

export function CompareWarnings({
  warnings,
  columns,
}: Pick<Schemas["CompareOut"], "warnings" | "columns">) {
  if (warnings.length === 0) return null;
  const occurrences = new Map<string, number>();

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      {warnings.map((warning) => {
        const identity = JSON.stringify([
          warning.code,
          warning.run_id,
          warning.split,
          warning.message,
        ]);
        const occurrence = occurrences.get(identity) ?? 0;
        occurrences.set(identity, occurrence + 1);
        const column = columns.find((item) => item.run_id === warning.run_id);
        const title =
          warning.code === "ORIGIN_SET_MISMATCH" && warning.split
            ? `${warning.split} 划分的评价起点集合不同`
            : (LABELS.get(warning.code) ?? "服务返回了对比警告");

        return (
          <Alert
            key={`${identity}:${occurrence}`}
            type="warning"
            showIcon
            style={{ overflowWrap: "anywhere" }}
            title={title}
            description={
              <>
                {warning.run_id && (
                  <div>
                    <span>
                      运行：{column ? `${column.name}（${warning.run_id}）` : warning.run_id}
                    </span>{" "}
                    {column && <StateTag state={column.state} />}
                  </div>
                )}
                <Typography.Text type="secondary">
                  {warning.code}：{warning.message}
                </Typography.Text>
              </>
            }
          />
        );
      })}
    </Space>
  );
}
