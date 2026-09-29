import { useMemo } from "react";
import { EChart, seriesColor, useChartColors } from "./EChart";

type Props = {
  metric: string;
  splits: string[];
  runs: { id: string; name: string }[];
  /** Split → run id → value. */
  values: Record<string, Record<string, number | null | undefined>>;
};

export function CompareBarChart({ metric, splits, runs, values }: Props) {
  const colors = useChartColors();
  const option = useMemo(
    () => ({
      tooltip: { trigger: "axis" as const },
      legend: {
        type: "scroll" as const,
        top: 0,
        textStyle: { color: colors.text },
      },
      grid: { left: 64, right: 24, top: 40, bottom: 32 },
      xAxis: {
        type: "category" as const,
        data: splits,
        axisLabel: { color: colors.secondary },
      },
      yAxis: {
        type: "value" as const,
        name: metric,
        axisLabel: { color: colors.secondary },
        splitLine: { lineStyle: { color: colors.border } },
      },
      series: runs.map((run, index) => ({
        name: run.name,
        type: "bar" as const,
        color: seriesColor(colors.series, index),
        data: splits.map((split) => values[split]?.[run.id] ?? null),
      })),
    }),
    [colors, metric, runs, splits, values],
  );
  return <EChart option={option} height={320} />;
}
