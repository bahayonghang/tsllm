import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Input,
  Select,
  Space,
  Table,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import type { Schemas } from "../api/client";
import { useDataset, useIngest, usePutChannels, useSeries } from "../api/hooks";
import { SegmentTimeline } from "../components/charts/SegmentTimeline";
import { SeriesChart } from "../components/charts/SeriesChart";
import { ErrorAlert } from "../components/ErrorAlert";
import { StateTag } from "../components/StateTag";
import { readDatasetMeta } from "../utils/datasetMeta";
import { formatDataTime, formatNumber, formatPercent } from "../utils/format";

type Channel = Schemas["ChannelSpec"];
type Role = NonNullable<Channel["role"]>;

const ROLE_LABELS: Record<Role, string> = {
  target: "目标",
  past_covariate: "历史协变量",
  known_future_covariate: "已知未来协变量",
  ignore: "忽略",
};
const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));
const DATA_TIME_FORMAT = "YYYY-MM-DDTHH:mm:ss";

function isRole(value: string): value is Role {
  return value in ROLE_LABELS;
}

export function DatasetDetailPage() {
  const datasetId = useParams().id ?? "";
  const navigate = useNavigate();
  const dataset = useDataset(datasetId);
  const putChannels = usePutChannels(datasetId);
  const ingest = useIngest();
  const [draft, setDraft] = useState<Channel[] | null>(null);
  const [needsIngest, setNeedsIngest] = useState(false);
  const [picked, setPicked] = useState<string[] | null>(null);
  const [range, setRange] = useState<{ start?: string; end?: string }>({});

  const data = dataset.data;
  const meta = readDatasetMeta(data?.meta);
  const channels: Channel[] =
    data?.config.channels ?? meta?.channelNames.map((name) => ({ name, role: "target" })) ?? [];
  const selected = picked ?? channels.slice(0, 1).map((channel) => channel.name);
  const fresh = data?.status === "fresh";
  const series = useSeries(datasetId, { channels: selected, ...range }, fresh);
  const units = Object.fromEntries(channels.map((channel) => [channel.name, channel.unit]));

  const runIngest = () =>
    ingest.mutate(datasetId, { onSuccess: (result) => navigate(`/runs/${result.run_id}`) });

  const updateDraft = (index: number, patch: Partial<Channel>) =>
    setDraft((rows) => rows?.map((row, i) => (i === index ? { ...row, ...patch } : row)) ?? null);

  const rows = draft ?? channels;

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Title level={3}>数据集 {datasetId}</Typography.Title>
      <ErrorAlert error={dataset.error ?? putChannels.error ?? ingest.error} />
      {data && (needsIngest || !fresh) && (
        <Alert
          type="warning"
          showIcon
          title={needsIngest ? "通道字典已修改，需要重新入库" : "数据集未入库或缓存已过期"}
          action={
            <Button size="small" type="primary" loading={ingest.isPending} onClick={runIngest}>
              {needsIngest || data.status === "stale" ? "重新入库" : "入库"}
            </Button>
          }
        />
      )}
      <Card size="small" loading={dataset.isLoading}>
        {data && (
          <Descriptions column={{ xs: 1, md: 3 }} size="small">
            <Descriptions.Item label="入库状态">
              <StateTag state={data.status} />
            </Descriptions.Item>
            <Descriptions.Item label="配置哈希">{data.config_hash}</Descriptions.Item>
            <Descriptions.Item label="频率">
              {data.config.native_freq} → {data.config.freq}
            </Descriptions.Item>
            <Descriptions.Item label="数据源">{data.config.source.path}</Descriptions.Item>
            <Descriptions.Item label="网格行数">{formatNumber(meta?.rows)}</Descriptions.Item>
            <Descriptions.Item label="运行段数">
              {formatNumber(meta?.segmentCount)}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Card
        size="small"
        title="通道"
        extra={
          draft === null ? (
            <Button
              size="small"
              disabled={channels.length === 0}
              onClick={() => setDraft(channels)}
            >
              编辑
            </Button>
          ) : (
            <Space>
              <Button size="small" onClick={() => setDraft(null)}>
                取消
              </Button>
              <Button
                size="small"
                type="primary"
                loading={putChannels.isPending}
                onClick={() =>
                  putChannels.mutate(draft, {
                    onSuccess: (result) => {
                      setDraft(null);
                      setNeedsIngest(result.needs_ingest);
                    },
                  })
                }
              >
                保存
              </Button>
            </Space>
          )
        }
      >
        <Table
          rowKey="name"
          size="small"
          pagination={false}
          scroll={{ x: "max-content" }}
          dataSource={rows}
          columns={[
            { title: "名称", dataIndex: "name" },
            {
              title: "角色",
              key: "role",
              render: (_, channel, index) =>
                draft === null ? (
                  ROLE_LABELS[channel.role ?? "target"]
                ) : (
                  <Select
                    size="small"
                    style={{ width: 150 }}
                    value={channel.role ?? "target"}
                    options={ROLE_OPTIONS}
                    onChange={(value: string) => {
                      if (isRole(value)) updateDraft(index, { role: value });
                    }}
                  />
                ),
            },
            {
              title: "单位",
              key: "unit",
              render: (_, channel, index) =>
                draft === null ? (
                  (channel.unit ?? "—")
                ) : (
                  <Input
                    size="small"
                    style={{ width: 100 }}
                    value={channel.unit ?? ""}
                    onChange={(event) => updateDraft(index, { unit: event.target.value || null })}
                  />
                ),
            },
            {
              title: "描述",
              key: "description",
              render: (_, channel, index) =>
                draft === null ? (
                  (channel.description ?? "—")
                ) : (
                  <Input
                    size="small"
                    style={{ width: 200 }}
                    value={channel.description ?? ""}
                    onChange={(event) =>
                      updateDraft(index, { description: event.target.value || null })
                    }
                  />
                ),
            },
            {
              title: "有效点均值",
              key: "mean",
              align: "right",
              render: (_, channel) => formatNumber(meta?.channels[channel.name]?.mean),
            },
            {
              title: "有效点标准差",
              key: "std",
              align: "right",
              render: (_, channel) => formatNumber(meta?.channels[channel.name]?.std),
            },
            {
              title: "缺失比例",
              key: "nullRate",
              align: "right",
              render: (_, channel) => formatPercent(meta?.channels[channel.name]?.nullRate),
            },
          ]}
        />
      </Card>

      {meta && (
        <Card size="small" title="运行段与划分">
          <SegmentTimeline segments={meta.segments} boundaries={meta.splitBoundaries} />
          <Typography.Text type="secondary">
            划分起点：
            {Object.entries(meta.splitBoundaries)
              .map(([split, time]) => `${split} ${formatDataTime(time)}`)
              .join("，")}
          </Typography.Text>
        </Card>
      )}

      {fresh && (
        <Card size="small" title="通道曲线">
          <Space wrap style={{ marginBottom: 12 }}>
            <Select
              mode="multiple"
              style={{ minWidth: 240, maxWidth: "100%" }}
              placeholder="选择通道"
              value={selected}
              options={channels.map((channel) => ({ value: channel.name, label: channel.name }))}
              onChange={(value: string[]) => setPicked(value)}
            />
            <DatePicker.RangePicker
              showTime
              value={range.start && range.end ? [dayjs(range.start), dayjs(range.end)] : undefined}
              onChange={(value) => {
                const [start, end] = value ?? [];
                setRange(
                  start && end
                    ? { start: start.format(DATA_TIME_FORMAT), end: end.format(DATA_TIME_FORMAT) }
                    : {},
                );
              }}
            />
            <Button onClick={() => setRange({})}>全部范围</Button>
          </Space>
          <ErrorAlert error={series.error} />
          {series.data && (
            <>
              <Typography.Text type="secondary">
                桶宽 {series.data.every}，共 {series.data.time.length}{" "}
                个点；缩放后按新范围重新加载。
              </Typography.Text>
              <SeriesChart
                time={series.data.time}
                values={series.data.values}
                units={units}
                onRangeChange={(start, end) => setRange({ start, end })}
              />
            </>
          )}
        </Card>
      )}
    </Space>
  );
}
