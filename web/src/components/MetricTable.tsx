import { Table } from "antd";
import { formatNumber } from "../utils/format";
import { columnsOf, type NumberTable } from "../utils/metrics";

type Props = {
  rowTitle: string;
  rows: NumberTable;
};

/** Rows keyed by split, lead, or channel; one column per metric. `null` shows as —. */
export function MetricTable({ rowTitle, rows }: Props) {
  const metrics = columnsOf(rows);
  return (
    <Table
      rowKey="key"
      size="small"
      pagination={false}
      scroll={{ x: "max-content" }}
      dataSource={Object.entries(rows).map(([key, values]) => ({
        key,
        values,
      }))}
      columns={[
        { title: rowTitle, dataIndex: "key", fixed: "left" },
        ...metrics.map((metric) => ({
          title: metric,
          key: metric,
          align: "right" as const,
          render: (_: unknown, row: { values: Record<string, number | null> }) =>
            formatNumber(row.values[metric]),
        })),
      ]}
    />
  );
}
