import { Card, Col, Descriptions, Row, Space } from "antd";
import type { RunDetail } from "../api/hooks";
import { formatNumber } from "../utils/format";
import type { RunMetrics } from "../utils/metrics";
import { ConfusionMatrix } from "./charts/ConfusionMatrix";
import { RocPrChart } from "./charts/RocPrChart";
import { MetricTable } from "./MetricTable";

type Threshold = NonNullable<
  Extract<NonNullable<RunDetail["job"]["run"]>["task"], { type: "classify" }>["label"]
>["threshold"];
type ThresholdBound = Extract<Threshold, { low: unknown }>["low"];

function describeBound(bound: ThresholdBound): string {
  if (typeof bound === "number") return `固定值 ${formatNumber(bound)}`;
  if (bound.value != null) return `固定值 ${formatNumber(bound.value)}`;
  return `fit 行分位数 ${formatNumber(bound.quantile ?? null)}`;
}

// The resolved threshold value is not exposed by the API; show the configured rule.
function describeThreshold(threshold: Threshold): string {
  if ("low" in threshold) {
    return `下限 ${describeBound(threshold.low)}；上限 ${describeBound(threshold.high)}`;
  }
  return describeBound(threshold);
}

type Props = {
  metrics: RunMetrics;
  job: RunDetail["job"];
};

export function ClassifyResults({ metrics, job }: Props) {
  const task = job.run?.task;
  const label = task?.type === "classify" ? task.label : null;
  const rows = Object.fromEntries(
    metrics.splits.map((item) => [item.split, { ...item.overall, n_origins: item.nOrigins }]),
  );
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Card size="small" title="划分指标">
        <MetricTable rowTitle="划分" rows={rows} />
      </Card>
      <Card size="small" title="ROC 与 PR 曲线">
        <RocPrChart
          roc={Object.fromEntries(metrics.splits.map((item) => [item.split, item.roc]))}
          pr={Object.fromEntries(metrics.splits.map((item) => [item.split, item.pr]))}
        />
      </Card>
      <Card size="small" title="混淆矩阵">
        <Row gutter={[16, 16]}>
          {metrics.splits.map((item) =>
            item.confusion ? (
              <Col key={item.split} xs={24} md={12}>
                <Card size="small" type="inner" title={item.split}>
                  <ConfusionMatrix matrix={item.confusion} />
                </Card>
              </Col>
            ) : null,
          )}
        </Row>
      </Card>
      {label && (
        <Card size="small" title="标签规则与阈值">
          <Descriptions column={{ xs: 1, md: 2 }} size="small">
            <Descriptions.Item label="规则">{label.type}</Descriptions.Item>
            <Descriptions.Item label="通道">{label.channel}</Descriptions.Item>
            <Descriptions.Item label="比较">{label.op}</Descriptions.Item>
            <Descriptions.Item label="事件阈值">
              {describeThreshold(label.threshold)}
            </Descriptions.Item>
            <Descriptions.Item label="未来窗口（步）">{label.window}</Descriptions.Item>
            <Descriptions.Item label="最短持续（步）">{label.min_duration}</Descriptions.Item>
            {metrics.splits.map((item) => (
              <Descriptions.Item key={item.split} label={`判决阈值（${item.split}）`}>
                {formatNumber(item.overall.threshold)}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </Card>
      )}
      <Card size="small" title="资源">
        <Descriptions column={{ xs: 1, md: 3 }} size="small">
          {Object.entries(metrics.resources).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {formatNumber(value)}
            </Descriptions.Item>
          ))}
        </Descriptions>
      </Card>
    </Space>
  );
}
