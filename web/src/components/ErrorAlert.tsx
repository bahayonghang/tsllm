import { Alert } from "antd";
import { ApiError } from "../api/client";
import { isRecord } from "../utils/guards";

const CODE_LABELS: Record<string, string> = {
  VALIDATION_ERROR: "参数校验失败",
  CAPABILITY_UNSUPPORTED: "基座不支持该配置",
  BACKBONE_LOAD_FAILED: "基座加载失败",
  TASK_CONFIG_INVALID: "任务配置无效",
  DATASET_NOT_FOUND: "数据集不存在",
  DATASET_NOT_INGESTED: "数据集未入库",
  CHANNEL_INVALID: "通道配置无效",
  RUN_NOT_FOUND: "运行不存在",
  RESULT_NOT_FOUND: "结果不存在",
  TEMPLATE_NOT_FOUND: "模板不存在",
  INVALID_TRANSITION: "状态不允许该操作",
  NOT_IMPLEMENTED: "功能未实现",
  NOT_FOUND: "资源不存在",
  INTERNAL_ERROR: "服务内部错误",
};

function detailLines(detail: unknown): string[] {
  if (!Array.isArray(detail)) return [];
  return detail.flatMap((item) => {
    if (!isRecord(item) || typeof item.msg !== "string") return [];
    const loc = Array.isArray(item.loc) ? item.loc.map(String).join(".") : "";
    return [loc ? `${loc}: ${item.msg}` : item.msg];
  });
}

export function ErrorAlert({ error }: { error: unknown }) {
  if (error === null || error === undefined) return null;
  if (error instanceof ApiError) {
    const lines = detailLines(error.detail);
    return (
      <Alert
        type="error"
        showIcon
        title={`${CODE_LABELS[error.code] ?? error.code}：${error.message}`}
        description={
          lines.length > 0 ? (
            <ul style={{ margin: 0, paddingInlineStart: 20 }}>
              {lines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : undefined
        }
      />
    );
  }
  const message = error instanceof Error ? error.message : String(error);
  return <Alert type="error" showIcon title={`请求失败：${message}`} />;
}
