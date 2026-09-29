import { Button, Space, Table, Typography } from "antd";
import { Link, useNavigate } from "react-router";
import { useDatasets, useIngest } from "../api/hooks";
import { ErrorAlert } from "../components/ErrorAlert";
import { StateTag } from "../components/StateTag";

export function DatasetsPage() {
  const navigate = useNavigate();
  const datasets = useDatasets();
  const ingest = useIngest();

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Title level={3}>数据集</Typography.Title>
      <ErrorAlert error={datasets.error ?? ingest.error} />
      <Table
        rowKey="id"
        size="small"
        loading={datasets.isLoading}
        dataSource={datasets.data ?? []}
        pagination={false}
        scroll={{ x: "max-content" }}
        columns={[
          {
            title: "ID",
            dataIndex: "id",
            render: (id: string) => <Link to={`/datasets/${encodeURIComponent(id)}`}>{id}</Link>,
          },
          {
            title: "数据源",
            key: "source",
            render: (_, item) =>
              `${item.config.source.path}（${item.config.source.format ?? "csv"}）`,
          },
          {
            title: "频率",
            key: "freq",
            render: (_, item) => `${item.config.native_freq} → ${item.config.freq}`,
          },
          {
            title: "通道数",
            key: "channels",
            render: (_, item) => item.config.channels?.length ?? "自动识别",
          },
          {
            title: "入库状态",
            dataIndex: "status",
            render: (status: string) => <StateTag state={status} />,
          },
          {
            title: "操作",
            key: "action",
            render: (_, item) =>
              item.status === "fresh" ? null : (
                <Button
                  size="small"
                  type="primary"
                  loading={ingest.isPending && ingest.variables === item.id}
                  onClick={() =>
                    ingest.mutate(item.id, {
                      onSuccess: (result) => navigate(`/runs/${result.run_id}`),
                    })
                  }
                >
                  入库
                </Button>
              ),
          },
        ]}
      />
    </Space>
  );
}
