import { useMemo } from "react";
import { formatDataTime, formatNumber } from "../../utils/format";
import { isRecord, numberOrNull } from "../../utils/guards";
import { EChart, useChartColors } from "./EChart";

type Props = {
  /** Context times followed by forecast times. */
  times: string[];
  context: (number | null)[];
  truth: (number | null)[];
  mean: (number | null)[];
  lower: (number | null)[] | null;
  upper: (number | null)[] | null;
  origin: string;
  unit?: string | null;
};

export function ForecastChart({ times, context, truth, mean, lower, upper, origin, unit }: Props) {
  const colors = useChartColors();

  const option = useMemo(() => {
    const band =
      lower && upper
        ? upper.map((value, i) => {
            const low = lower[i];
            return value === null || low === null || low === undefined ? null : value - low;
          })
        : null;
    const rows: [string, (number | null)[] | null][] = [
      ["上下文", context],
      ["真值", truth],
      ["预测均值", mean],
      ["q0.1", lower],
      ["q0.9", upper],
    ];
    return {
      tooltip: {
        trigger: "axis" as const,
        formatter: (params: unknown) => {
          const first = Array.isArray(params) ? params[0] : params;
          const index = isRecord(first) ? numberOrNull(first.dataIndex) : null;
          if (index === null) return "";
          const lines = rows
            .filter(([, values]) => values?.[index] !== null && values?.[index] !== undefined)
            .map(([name, values]) => `${name}：${formatNumber(values?.[index])}`);
          return [formatDataTime(times[index]), ...lines].join("<br/>");
        },
      },
      legend: {
        top: 0,
        data: ["上下文", "真值", "预测均值", "10–90% 分位带"],
        textStyle: { color: colors.text },
      },
      grid: { left: 56, right: 24, top: 40, bottom: 56 },
      xAxis: {
        type: "category" as const,
        data: times,
        axisLabel: { color: colors.secondary, hideOverlap: true, formatter: formatDataTime },
      },
      yAxis: {
        type: "value" as const,
        scale: true,
        name: unit ?? "",
        axisLabel: { color: colors.secondary },
        splitLine: { lineStyle: { color: colors.border } },
      },
      dataZoom: [{ type: "inside" as const }],
      series: [
        {
          name: "上下文",
          type: "line" as const,
          showSymbol: false,
          color: colors.secondary,
          data: context,
          markLine: {
            symbol: "none",
            silent: true,
            lineStyle: { color: colors.secondary, type: "dashed" as const },
            label: { formatter: "起点", color: colors.secondary },
            data: [{ xAxis: origin }],
          },
        },
        {
          name: "真值",
          type: "line" as const,
          showSymbol: false,
          color: colors.series[1],
          data: truth,
        },
        {
          name: "预测均值",
          type: "line" as const,
          showSymbol: false,
          color: colors.series[0],
          data: mean,
        },
        ...(lower && band
          ? [
              {
                name: "10–90% 分位带",
                type: "line" as const,
                stack: "band",
                showSymbol: false,
                lineStyle: { opacity: 0 },
                color: colors.series[0],
                data: lower,
              },
              {
                name: "10–90% 分位带",
                type: "line" as const,
                stack: "band",
                showSymbol: false,
                lineStyle: { opacity: 0 },
                areaStyle: { opacity: 0.2 },
                color: colors.series[0],
                data: band,
              },
            ]
          : []),
      ],
    };
  }, [colors, context, lower, mean, origin, times, truth, unit, upper]);

  return <EChart option={option} height={360} />;
}
