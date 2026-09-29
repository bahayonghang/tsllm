import { Tag } from "antd";

const STATES: Record<string, { color: string; label: string }> = {
  queued: { color: "default", label: "排队中" },
  running: { color: "processing", label: "运行中" },
  succeeded: { color: "success", label: "成功" },
  failed: { color: "error", label: "失败" },
  cancelled: { color: "warning", label: "已取消" },
  interrupted: { color: "warning", label: "已中断" },
  fresh: { color: "success", label: "已入库" },
  stale: { color: "warning", label: "已过期" },
  missing: { color: "default", label: "未入库" },
};

export function StateTag({ state }: { state: string }) {
  const item = STATES[state];
  return <Tag color={item?.color ?? "default"}>{item?.label ?? state}</Tag>;
}
