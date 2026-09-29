import { Card, Descriptions, Select, Space, Typography } from "antd";
import { useSearchParams } from "react-router";
import {
  isSplit,
  type RunDetail,
  usePredictionOrigins,
  usePredictionRows,
  useSeries,
} from "../api/hooks";
import { formatDataTime, formatNumber, shiftDataTime } from "../utils/format";
import { isRecord, numberOrNull } from "../utils/guards";
import type { RunMetrics } from "../utils/metrics";
import { ForecastChart } from "./charts/ForecastChart";
import { ErrorAlert } from "./ErrorAlert";
import { MetricTable } from "./MetricTable";

type Props = {
  runId: string;
  metrics: RunMetrics;
  job: RunDetail["job"];
};

type Point = {
  lead: number;
  truth: number | null;
  mean: number | null;
  quantiles: Map<number, number | null>;
};

function readPoints(rows: unknown[] | null | undefined, channel: string): Point[] {
  const points: Point[] = [];
  for (const row of rows ?? []) {
    if (!isRecord(row) || row.channel !== channel) continue;
    const lead = numberOrNull(row.lead);
    if (lead === null) continue;
    const quantiles = new Map<number, number | null>();
    for (const [key, value] of Object.entries(row)) {
      const level = key.startsWith("q_") ? Number(key.slice(2)) : Number.NaN;
      if (!Number.isNaN(level)) quantiles.set(level, numberOrNull(value));
    }
    points.push({
      lead,
      truth: numberOrNull(row.y_true),
      mean: numberOrNull(row.y_pred),
      quantiles,
    });
  }
  return points.sort((a, b) => a.lead - b.lead);
}

function nearestLevel(levels: number[], target: number): number | undefined {
  let best: number | undefined;
  for (const level of levels) {
    if (best === undefined || Math.abs(level - target) < Math.abs(best - target)) best = level;
  }
  return best !== undefined && Math.abs(best - target) <= 0.05 ? best : undefined;
}

export function ForecastResults({ runId, metrics, job }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const splitNames = metrics.splits.map((item) => item.split).filter(isSplit);
  const splitParam = searchParams.get("split");
  const split =
    splitParam && isSplit(splitParam) && splitNames.includes(splitParam)
      ? splitParam
      : (splitNames.find((name) => name === "test") ?? splitNames[0] ?? null);
  const current = metrics.splits.find((item) => item.split === split);
  const channels = Object.keys(current?.perChannel ?? {});
  const channel = searchParams.get("channel") ?? channels[0] ?? null;

  const originsQuery = usePredictionOrigins(runId, split);
  const origins = originsQuery.data?.origins ?? [];
  const origin = searchParams.get("origin") ?? origins[0] ?? null;
  const rowsQuery = usePredictionRows(runId, split, channel, origin);

  const contextLength = job.run?.task.context_length ?? 0;
  const freq = job.dataset.freq;
  const contextStart = origin ? shiftDataTime(origin, freq, -(contextLength - 1)) : null;
  const context = useSeries(
    job.dataset.id,
    {
      channels: channel ? [channel] : [],
      start: contextStart ?? undefined,
      end: origin ?? undefined,
      maxPoints: contextLength + 1,
    },
    origin !== null && contextStart !== null,
  );

  const setParam = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === "split") next.delete("origin");
    setSearchParams(next, { replace: true });
  };

  const points = channel ? readPoints(rowsQuery.data?.rows, channel) : [];
  const levels = [...new Set(points.flatMap((point) => [...point.quantiles.keys()]))];
  const lowLevel = nearestLevel(levels, 0.1);
  const highLevel = nearestLevel(levels, 0.9);
  const contextTimes = context.data?.time ?? [];
  const contextValues = channel ? (context.data?.values[channel] ?? []) : [];
  const futureTimes = origin
    ? points.map((point) => shiftDataTime(origin, freq, point.lead) ?? `+${point.lead}`)
    : [];
  const pad = contextTimes.map(() => null);
  const unit = job.dataset.channels?.find((item) => item.name === channel)?.unit;

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Card size="small" title="划分指标">
        <MetricTable
          rowTitle="划分"
          rows={Object.fromEntries(metrics.splits.map((item) => [item.split, item.overall]))}
        />
      </Card>
      <Card size="small" title="预测曲线">
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            style={{ width: 110 }}
            value={split ?? undefined}
            options={splitNames.map((name) => ({ value: name, label: name }))}
            onChange={(value: string) => setParam("split", value)}
          />
          <Select
            style={{ minWidth: 200, maxWidth: "100%" }}
            showSearch
            value={channel ?? undefined}
            options={channels.map((name) => ({ value: name, label: name }))}
            onChange={(value: string) => setParam("channel", value)}
          />
          <Select
            style={{ width: 230 }}
            showSearch
            loading={originsQuery.isLoading}
            value={origin ?? undefined}
            options={origins.map((time) => ({
              value: time,
              label: formatDataTime(time),
            }))}
            onChange={(value: string) => setParam("origin", value)}
          />
        </Space>
        {originsQuery.data && (
          <Typography.Paragraph type="secondary">
            起点 {origins.length} / {originsQuery.data.total_origins ?? origins.length}{" "}
            个（均匀抽取）。
          </Typography.Paragraph>
        )}
        <ErrorAlert error={originsQuery.error ?? rowsQuery.error ?? context.error} />
        {origin && points.length > 0 && (
          <ForecastChart
            times={[...contextTimes, ...futureTimes]}
            context={[...contextValues, ...points.map(() => null)]}
            truth={[...pad, ...points.map((point) => point.truth)]}
            mean={[...pad, ...points.map((point) => point.mean)]}
            lower={
              lowLevel === undefined
                ? null
                : [...pad, ...points.map((point) => point.quantiles.get(lowLevel) ?? null)]
            }
            upper={
              highLevel === undefined
                ? null
                : [...pad, ...points.map((point) => point.quantiles.get(highLevel) ?? null)]
            }
            origin={contextTimes[contextTimes.length - 1] ?? origin}
            unit={unit}
          />
        )}
      </Card>
      {current && Object.keys(current.perLead).length > 0 && (
        <Card size="small" title={`按提前量（${current.split}）`}>
          <MetricTable rowTitle="提前量（步）" rows={current.perLead} />
        </Card>
      )}
      {current && channels.length > 0 && (
        <Card size="small" title={`按通道（${current.split}）`}>
          <MetricTable rowTitle="通道" rows={current.perChannel} />
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
