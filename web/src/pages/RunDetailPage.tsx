import {
  Alert,
  Button,
  Card,
  Collapse,
  Descriptions,
  Popconfirm,
  Progress,
  Space,
  Typography,
} from "antd";
import { Link, useParams } from "react-router";
import { ACTIVE_STATES, useCancelRun, useMetrics, useRun } from "../api/hooks";
import { type RunEvent, useRunEvents } from "../api/sse";
import { ClassifyResults } from "../components/ClassifyResults";
import { ErrorAlert } from "../components/ErrorAlert";
import { ForecastResults } from "../components/ForecastResults";
import { RunLog } from "../components/RunLog";
import { StateTag } from "../components/StateTag";
import { formatSystemTime } from "../utils/format";
import { readMetrics } from "../utils/metrics";

function currentProgress(events: RunEvent[]): { stage: string | null; percent: number | null } {
  let stage: string | null = null;
  let percent: number | null = null;
  for (const event of events) {
    if (event.kind === "stage") {
      stage = typeof event.data.name === "string" ? event.data.name : stage;
      percent = null;
    } else if (event.kind === "progress") {
      const { step, total } = event.data;
      if (typeof step === "number" && typeof total === "number" && total > 0) {
        percent = Math.round((step / total) * 100);
      }
    }
  }
  return { stage, percent };
}

export function RunDetailPage() {
  const runId = useParams().id ?? "";
  const run = useRun(runId);
  const cancel = useCancelRun(runId);
  const stream = useRunEvents(runId, run.data !== undefined);

  const data = run.data;
  const state = data?.status.state;
  const active = state !== undefined && ACTIVE_STATES.includes(state);
  const isExperiment = data?.job.run !== null && data?.job.run !== undefined;
  const metrics = useMetrics(runId, state === "succeeded" && isExperiment);
  const parsed = metrics.data ? readMetrics(metrics.data) : null;
  const progress = currentProgress(stream.events);

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Space wrap align="center">
        <Typography.Title level={3} style={{ margin: 0 }}>
          {data?.job.run?.name ?? runId}
        </Typography.Title>
        {state && <StateTag state={state} />}
        {active && (
          <Popconfirm
            title="确认取消该运行？"
            okText="取消运行"
            cancelText="返回"
            onConfirm={() => cancel.mutate()}
          >
            <Button danger loading={cancel.isPending}>
              取消
            </Button>
          </Popconfirm>
        )}
        {isExperiment && (
          <Link to={`/runs/new?from=${encodeURIComponent(runId)}`}>以此配置新建</Link>
        )}
      </Space>
      <ErrorAlert error={run.error ?? cancel.error} />
      {data?.status.error && (
        <Alert type="error" showIcon title="运行失败" description={data.status.error} />
      )}

      <Card size="small" loading={run.isLoading}>
        {data && (
          <Descriptions column={{ xs: 1, md: 3 }} size="small">
            <Descriptions.Item label="运行 ID">{data.run_id}</Descriptions.Item>
            <Descriptions.Item label="作业类型">{data.job.kind}</Descriptions.Item>
            <Descriptions.Item label="数据集">
              <Link to={`/datasets/${encodeURIComponent(data.job.dataset.id)}`}>
                {data.job.dataset.id}
              </Link>
            </Descriptions.Item>
            <Descriptions.Item label="基座">{data.job.run?.backbone.name ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="模式">{data.job.run?.mode ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="任务">{data.job.run?.task.type ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {formatSystemTime(data.status.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {formatSystemTime(data.status.started_at)}
            </Descriptions.Item>
            <Descriptions.Item label="结束时间">
              {formatSystemTime(data.status.finished_at)}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Card size="small" title="进度与日志">
        {progress.stage && (
          <Space wrap style={{ marginBottom: 8 }}>
            <Typography.Text>阶段：{progress.stage}</Typography.Text>
            {progress.percent !== null && (
              <Progress
                percent={progress.percent}
                size="small"
                style={{ width: 200 }}
                status={active ? "active" : undefined}
              />
            )}
          </Space>
        )}
        <RunLog
          events={stream.events}
          dropped={stream.dropped}
          error={stream.ended ? null : stream.error}
        />
      </Card>

      {data && (
        <Collapse
          items={[
            {
              key: "config",
              label: "配置快照",
              children: (
                <pre style={{ margin: 0, overflow: "auto" }}>
                  {JSON.stringify(data.job.run ?? data.job.dataset, null, 2)}
                </pre>
              ),
            },
            {
              key: "env",
              label: "环境快照",
              children: (
                <pre style={{ margin: 0, overflow: "auto" }}>
                  {data.env ? JSON.stringify(data.env, null, 2) : "尚无环境快照"}
                </pre>
              ),
            },
          ]}
        />
      )}

      <ErrorAlert error={metrics.error} />
      {parsed && parsed.warnings.length > 0 && (
        <Alert type="warning" showIcon title="指标警告" description={parsed.warnings.join("；")} />
      )}
      {data && parsed?.task === "forecast" && (
        <ForecastResults runId={runId} metrics={parsed} job={data.job} />
      )}
      {data && parsed?.task === "classify" && <ClassifyResults metrics={parsed} job={data.job} />}
    </Space>
  );
}
