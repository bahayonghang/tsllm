import { Table } from "antd";

type Props = {
  /** 2×2 counts; rows are true labels 0 and 1, columns are predicted labels 0 and 1. */
  matrix: number[][];
};

export function ConfusionMatrix({ matrix }: Props) {
  const rows = [0, 1].map((label) => ({
    key: label,
    label: `真实 ${label}`,
    predicted0: matrix[label]?.[0] ?? 0,
    predicted1: matrix[label]?.[1] ?? 0,
  }));
  return (
    <Table
      size="small"
      pagination={false}
      bordered
      dataSource={rows}
      columns={[
        { title: "", dataIndex: "label" },
        { title: "预测 0", dataIndex: "predicted0", align: "right" },
        { title: "预测 1", dataIndex: "predicted1", align: "right" },
      ]}
    />
  );
}
