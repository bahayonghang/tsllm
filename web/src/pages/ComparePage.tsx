import { Alert, Card, Select, Space, Table, Typography } from "antd";
import { Link, useSearchParams } from "react-router";
import { useCompare, useRuns } from "../api/hooks";
import { CompareBarChart } from "../components/charts/CompareBarChart";
import { ErrorAlert } from "../components/ErrorAlert";
import { StateTag } from "../components/StateTag";
import { formatNumber } from "../utils/format";

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runIds = (searchParams.get("run_ids") ?? "").split(",").filter((id) => id !== "");
  const runs = useRuns();
  const compare = useCompare(runIds);
  const data = compare.data;

  const metricNames = [...new Set((data?.rows ?? []).map((row) => row.metric))];
  const metricParam = searchParams.get("metric");
  const metric = metricParam && metricNames.includes(metricParam) ? metricParam : metricNames[0];
  const metricRows = (data?.rows ?? []).filter((row) => row.metric === metric);

  const setParam = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  const columns = data?.columns ?? [];
  const runLabel = (id: string) => columns.find((column) => column.run_id === id)?.name ?? id;

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Title level={3}>对比</Typography.Title>
      <Select
        mode="multiple"
        allowClear
        style={{ width: "100%" }}
        placeholder="选择要对比的运行"
        value={runIds}
        loading={runs.isLoading}
        options={(runs.data ?? [])
          .filter((run) => run.kind === "experiment")
          .map((run) => ({
            value: run.run_id,
            label: `${run.name}（${run.run_id}）`,
          }))}
        onChange={(value: string[]) => setParam("run_ids", value.join(","))}
      />
      <ErrorAlert error={runs.error ?? compare.error} />
      {data?.warnings.map((warning) => (
        <Alert
          key={`${warning.code}:${warning.message}`}
          type="warning"
          showIcon
          title={warning.message}
          description={warning.code}
        />
      ))}
      {data && (
        <>
          <Card size="small" title="运行">
            <Table
              rowKey="run_id"
              size="small"
              pagination={false}
              scroll={{ x: "max-content" }}
              dataSource={columns}
              columns={[
                {
                  title: "名称",
                  dataIndex: "name",
                  render: (name: string, column) => (
                    <Link to={`/runs/${column.run_id}`}>{name}</Link>
                  ),
                },
                {
                  title: "状态",
                  dataIndex: "state",
                  render: (state: string) => <StateTag state={state} />,
                },
                { title: "数据集", dataIndex: "dataset" },
                {
                  title: "任务",
                  dataIndex: "task",
                  render: (value: string | null) => value ?? "—",
                },
                {
                  title: "基座",
                  dataIndex: "backbone",
                  render: (value: string | null) => value ?? "—",
                },
                {
                  title: "模式",
                  dataIndex: "mode",
                  render: (value: string | null) => value ?? "—",
                },
                {
                  title: "上下文长度",
                  dataIndex: "context_length",
                  render: (value: number | null) => formatNumber(value),
                },
                {
                  title: "预测步长",
                  dataIndex: "horizon",
                  render: (value: number | null) => formatNumber(value),
                },
              ]}
            />
          </Card>
          <Card size="small" title="指标">
            <Table
              rowKey={(row) => `${row.split}:${row.metric}`}
              size="small"
              pagination={false}
              scroll={{ x: "max-content" }}
              dataSource={data.rows}
              columns={[
                { title: "划分", dataIndex: "split", fixed: "left" },
                { title: "指标", dataIndex: "metric", fixed: "left" },
                ...columns.map((column) => ({
                  title: column.name,
                  key: column.run_id,
                  align: "right" as const,
                  render: (_: unknown, row: (typeof data.rows)[number]) =>
                    formatNumber(row.values[column.run_id]),
                })),
              ]}
            />
          </Card>
          {metric && (
            <Card
              size="small"
              title="指标柱状图"
              extra={
                <Select
                  size="small"
                  style={{ width: 180 }}
                  value={metric}
                  options={metricNames.map((name) => ({ value: name, label: name }))}
                  onChange={(value: string) => setParam("metric", value)}
                />
              }
            >
              <CompareBarChart
                metric={metric}
                splits={metricRows.map((row) => row.split)}
                runs={columns.map((column) => ({
                  id: column.run_id,
                  name: runLabel(column.run_id),
                }))}
                values={Object.fromEntries(metricRows.map((row) => [row.split, row.values]))}
              />
            </Card>
          )}
        </>
      )}
    </Space>
  );
}
