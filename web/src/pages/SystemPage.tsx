import { Card, Descriptions, Space, Table, Typography } from "antd";
import { useSystem } from "../api/hooks";
import { ErrorAlert } from "../components/ErrorAlert";
import { formatMegabytes } from "../utils/format";

export function SystemPage() {
  const system = useSystem();
  const data = system.data;
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Title level={3}>系统</Typography.Title>
      <ErrorAlert error={system.error} />
      <Card title="运行环境" loading={system.isLoading}>
        {data && (
          <Descriptions column={{ xs: 1, md: 2 }} size="small">
            <Descriptions.Item label="Python">{data.python}</Descriptions.Item>
            <Descriptions.Item label="平台">{data.platform}</Descriptions.Item>
            <Descriptions.Item label="运行目录">{data.runs_dir}</Descriptions.Item>
            <Descriptions.Item label="缓存目录">{data.cache_dir}</Descriptions.Item>
            <Descriptions.Item label="配置目录">{data.configs_dir}</Descriptions.Item>
            <Descriptions.Item label="并发槽位">
              GPU {data.gpu_slots}，CPU {data.cpu_slots}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>
      <Card title="GPU" loading={system.isLoading}>
        <Table
          rowKey="index"
          size="small"
          pagination={false}
          scroll={{ x: "max-content" }}
          dataSource={data?.gpus ?? []}
          locale={{ emptyText: "未检测到 GPU" }}
          columns={[
            { title: "序号", dataIndex: "index" },
            { title: "名称", dataIndex: "name" },
            {
              title: "显存（已用 / 总量）",
              key: "memory",
              render: (_, gpu) =>
                `${formatMegabytes(gpu.memory_used_mb)} / ${formatMegabytes(gpu.memory_total_mb)}`,
            },
            { title: "驱动版本", dataIndex: "driver_version" },
          ]}
        />
      </Card>
      <Card title="库版本" loading={system.isLoading}>
        <Table
          rowKey="name"
          size="small"
          pagination={false}
          scroll={{ x: "max-content" }}
          dataSource={Object.entries(data?.packages ?? {}).map(([name, version]) => ({
            name,
            version: version ?? "未安装",
          }))}
          columns={[
            { title: "包", dataIndex: "name" },
            { title: "版本", dataIndex: "version" },
          ]}
        />
      </Card>
    </Space>
  );
}
