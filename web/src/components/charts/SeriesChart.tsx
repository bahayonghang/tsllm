import { useEffect, useMemo, useRef } from "react";
import { isRecord, numberOrNull } from "../../utils/guards";
import { EChart, seriesColor, useChartColors } from "./EChart";

type Props = {
  time: string[];
  values: Record<string, (number | null)[]>;
  units: Record<string, string | null | undefined>;
  /** Called with the data times of the zoomed window after the user stops zooming. */
  onRangeChange?: (start: string, end: string) => void;
};

function zoomPercent(params: unknown): { start: number; end: number } | null {
  const item = isRecord(params) && Array.isArray(params.batch) ? params.batch[0] : params;
  if (!isRecord(item)) return null;
  const start = numberOrNull(item.start);
  const end = numberOrNull(item.end);
  return start === null || end === null ? null : { start, end };
}

export function SeriesChart({ time, values, units, onRangeChange }: Props) {
  const colors = useChartColors();
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const names = Object.keys(values);
  const unitSet = new Set(names.map((name) => units[name] ?? ""));
  const axisName = unitSet.size === 1 ? [...unitSet][0] : "";

  const option = useMemo(
    () => ({
      color: colors.series,
      tooltip: { trigger: "axis" as const },
      legend: {
        type: "scroll" as const,
        top: 0,
        textStyle: { color: colors.text },
      },
      grid: { left: 56, right: 24, top: 40, bottom: 72 },
      xAxis: {
        type: "time" as const,
        axisLabel: { color: colors.secondary, hideOverlap: true },
      },
      yAxis: {
        type: "value" as const,
        scale: true,
        name: axisName,
        axisLabel: { color: colors.secondary },
        splitLine: { lineStyle: { color: colors.border } },
      },
      dataZoom: [{ type: "inside" as const }, { type: "slider" as const, bottom: 16 }],
      series: names.map((name, index) => ({
        name: units[name] ? `${name}（${units[name]}）` : name,
        type: "line" as const,
        showSymbol: false,
        connectNulls: false,
        color: seriesColor(colors.series, index),
        data: time.map((t, i) => [t, values[name]?.[i] ?? null]),
      })),
    }),
    [axisName, colors, names, time, units, values],
  );

  const onEvents = useMemo(
    () => ({
      datazoom: (params: unknown) => {
        const zoom = zoomPercent(params);
        if (!onRangeChange || zoom === null || time.length < 2) return;
        if (zoom.start <= 0 && zoom.end >= 100) return;
        const last = time.length - 1;
        const first = time[Math.floor((zoom.start / 100) * last)];
        const final = time[Math.ceil((zoom.end / 100) * last)];
        if (first === undefined || final === undefined) return;
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => onRangeChange(first, final), 500);
      },
    }),
    [onRangeChange, time],
  );

  return <EChart option={option} height={360} onEvents={onEvents} />;
}
