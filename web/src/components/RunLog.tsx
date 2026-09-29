import { Alert, Typography, theme } from "antd";
import { useEffect, useRef } from "react";
import type { RunEvent } from "../api/sse";
import { formatNumber, formatSystemTime } from "../utils/format";

type Props = {
  events: RunEvent[];
  dropped: number;
  error: string | null;
};

function describe(event: RunEvent): string {
  const { data } = event;
  switch (event.kind) {
    case "log":
      return `[${String(data.level ?? "info")}] ${String(data.msg ?? "")}`;
    case "stage":
      return `阶段：${String(data.name ?? "")}`;
    case "progress":
      return `进度：${String(data.stage ?? "")} ${String(data.step ?? "")}/${String(data.total ?? "")}`;
    case "metric": {
      const value = typeof data.value === "number" ? formatNumber(data.value) : String(data.value);
      const step = data.step === null || data.step === undefined ? "" : ` @${String(data.step)}`;
      return `指标：${String(data.name ?? "")} = ${value}${step}`;
    }
    default:
      return JSON.stringify(data);
  }
}

export function RunLog({ events, dropped, error }: Props) {
  const { token } = theme.useToken();
  const box = useRef<HTMLDivElement>(null);
  const count = events.length;

  // Keep the newest line visible.
  useEffect(() => {
    if (count > 0 && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [count]);

  return (
    <>
      {error && <Alert type="warning" showIcon title={error} style={{ marginBottom: 8 }} />}
      {dropped > 0 && (
        <Typography.Text type="secondary">已丢弃最早的 {dropped} 条事件。</Typography.Text>
      )}
      <div
        ref={box}
        role="log"
        style={{
          height: 320,
          overflow: "auto",
          fontFamily: token.fontFamilyCode,
          fontSize: 12,
          background: token.colorFillQuaternary,
          padding: 8,
          borderRadius: token.borderRadius,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {events.length === 0 && <Typography.Text type="secondary">暂无事件</Typography.Text>}
        {events.map((event) => (
          <div key={event.id} data-event-id={event.id}>
            <span style={{ color: token.colorTextSecondary }}>
              {formatSystemTime(typeof event.data.ts === "string" ? event.data.ts : null)}
            </span>{" "}
            {describe(event)}
          </div>
        ))}
      </div>
    </>
  );
}
