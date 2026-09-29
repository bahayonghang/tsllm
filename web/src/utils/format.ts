import dayjs from "dayjs";

export const EMPTY = "—";

/** Data times have no time zone. Show the wall-clock value unchanged. */
export function formatDataTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  return value.replace("T", " ");
}

/** System times are UTC with an offset. Show them in the browser time zone. */
export function formatSystemTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  return dayjs(value).format("YYYY-MM-DD HH:mm:ss");
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  if (Number.isInteger(value)) return String(value);
  if (Math.abs(value) >= 1000) return value.toFixed(1);
  return String(Number(value.toPrecision(4)));
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  return `${(value * 100).toFixed(1)}%`;
}

export function formatMegabytes(value: number | null | undefined): string {
  if (value === null || value === undefined) return EMPTY;
  return `${Math.round(value).toLocaleString("zh-CN")} MiB`;
}

const UNIT_MS: Record<string, number> = {
  us: 0.001,
  ms: 1,
  s: 1000,
  min: 60_000,
  h: 3_600_000,
  d: 86_400_000,
};

/** Milliseconds of a duration string such as `10s`, `5min`, `1h`. */
export function durationMs(freq: string): number | null {
  const match = /^([0-9]+(?:\.[0-9]+)?)(us|ms|s|min|h|d)$/.exec(freq);
  if (!match?.[1] || !match[2]) return null;
  const unit = UNIT_MS[match[2]];
  return unit === undefined ? null : Number(match[1]) * unit;
}

/**
 * Shift a data time by `steps` grid intervals. The arithmetic runs in UTC on the
 * wall-clock value, so no time zone conversion happens.
 */
export function shiftDataTime(value: string, freq: string, steps: number): string | null {
  const step = durationMs(freq);
  const base = Date.parse(`${value.slice(0, 19)}Z`);
  if (step === null || Number.isNaN(base)) return null;
  return new Date(base + step * steps).toISOString().slice(0, 19);
}
