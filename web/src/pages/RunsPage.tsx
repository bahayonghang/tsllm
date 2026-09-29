import { Button, Select, Space, Table, Typography } from "antd";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import type { Schemas } from "../api/client";
import { useRuns } from "../api/hooks";
import { ErrorAlert } from "../components/ErrorAlert";
import { StateTag } from "../components/StateTag";
import { formatNumber, formatSystemTime } from "../utils/format";

type Run = Schemas["RunSummary"];

const FILTERS = [
  { key: "state", label: "状态" },
  { key: "type", label: "类型" },
  { key: "dataset", label: "数据集" },
] as const;

function runType(run: Run): string {
  return run.task ?? run.kind;
}

function filterValue(run: Run, key: (typeof FILTERS)[number]["key"]): string {
  if (key === "type") return runType(run);
  return run[key];
}

export function RunsPage() {
  const navigate = useNavigate();
  const runs = useRuns();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<string[]>([]);

  const all = runs.data ?? [];
  const visible = all.filter((run) =>
    FILTERS.every(({ key }) => {
      const wanted = searchParams.get(key);
      return !wanted || filterValue(run, key) === wanted;
    }),
  );

  const setFilter = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Title level={3}>运行</Typography.Title>
      <ErrorAlert error={runs.error} />
      <Space wrap>
        {FILTERS.map(({ key, label }) => (
          <Select
            key={key}
            allowClear
            style={{ width: 160 }}
            placeholder={label}
            value={searchParams.get(key) ?? undefined}
            options={[...new Set(all.map((run) => filterValue(run, key)))].map((value) => ({
              value,
              label: value,
            }))}
            onChange={(value: string | undefined) => setFilter(key, value)}
          />
        ))}
        <Button
          type="primary"
          disabled={selected.length === 0}
          onClick={() => navigate(`/compare?run_ids=${selected.join(",")}`)}
        >
          对比所选（{selected.length}）
        </Button>
        <Button onClick={() => navigate("/runs/new")}>新建运行</Button>
      </Space>
      <Table
        rowKey="run_id"
        size="small"
        loading={runs.isLoading}
        dataSource={visible}
        scroll={{ x: "max-content" }}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (keys) => setSelected(keys.map(String)),
          // An ingest job has no metrics to compare.
          getCheckboxProps: (run) => ({ disabled: run.kind !== "experiment" }),
        }}
        columns={[
          {
            title: "状态",
            dataIndex: "state",
            render: (state: string) => <StateTag state={state} />,
          },
          {
            title: "名称",
            dataIndex: "name",
            render: (name: string, run) => <Link to={`/runs/${run.run_id}`}>{name}</Link>,
          },
          { title: "类型", key: "type", render: (_, run) => runType(run) },
          { title: "数据集", dataIndex: "dataset" },
          { title: "基座", dataIndex: "backbone", render: (value: string | null) => value ?? "—" },
          { title: "模式", dataIndex: "mode", render: (value: string | null) => value ?? "—" },
          {
            title: "创建时间",
            dataIndex: "created_at",
            render: (value: string) => formatSystemTime(value),
          },
          {
            title: "结束时间",
            dataIndex: "finished_at",
            render: (value: string | null) => formatSystemTime(value),
          },
          {
            title: "主要指标",
            key: "primary",
            render: (_, run) =>
              run.primary_metric ? `${run.primary_metric} ${formatNumber(run.primary_value)}` : "—",
          },
        ]}
      />
    </Space>
  );
}
