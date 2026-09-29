import type { CustomSeriesRenderItem } from "echarts";
import { useMemo } from "react";
import { formatDataTime } from "../../utils/format";
import { EChart, seriesColor, useChartColors } from "./EChart";

type Interval = { start: string; end: string };

type Props = {
  segments: Interval[];
  /** Start time of each split after `fit`, for example `{ val, cal, test }`. */
  boundaries: Record<string, string>;
};

const SPLITS = ["fit", "val", "cal", "test"];
const ROWS = ["运行段", "划分"];

export function SegmentTimeline({ segments, boundaries }: Props) {
  const colors = useChartColors();

  const option = useMemo(() => {
    const first = segments[0]?.start;
    const last = segments[segments.length - 1]?.end;
    const starts = SPLITS.map((split, index) => (index === 0 ? first : boundaries[split]));
    const splitItems = SPLITS.flatMap((split, index) => {
      const start = starts[index];
      const end = starts.slice(index + 1).find((value) => value !== undefined) ?? last;
      return start && end ? [{ value: [start, end, 1, index], name: split }] : [];
    });
    const segmentItems = segments.map((segment, index) => ({
      value: [segment.start, segment.end, 0, -1],
      name: `段 ${index}`,
    }));

    const renderItem: CustomSeriesRenderItem = (_params, api) => {
      const start = api.coord([api.value(0), api.value(2)]);
      const end = api.coord([api.value(1), api.value(2)]);
      const size = api.size?.([0, 1]);
      const rowHeight = Array.isArray(size) ? (size[1] ?? 20) : 20;
      const splitIndex = Number(api.value(3));
      const height = rowHeight * 0.6;
      return {
        type: "rect",
        shape: {
          x: start[0] ?? 0,
          y: (start[1] ?? 0) - height / 2,
          width: Math.max((end[0] ?? 0) - (start[0] ?? 0), 1),
          height,
        },
        style: {
          fill: splitIndex >= 0 ? seriesColor(colors.series, splitIndex) : colors.secondary,
        },
      };
    };

    return {
      tooltip: {
        formatter: (params: unknown) => {
          const item = Array.isArray(params) ? params[0] : params;
          if (typeof item !== "object" || item === null || !("value" in item)) return "";
          const value = Array.isArray(item.value) ? item.value : [];
          const name = "name" in item ? String(item.name) : "";
          return `${name}<br/>${formatDataTime(String(value[0]))} — ${formatDataTime(String(value[1]))}`;
        },
      },
      grid: { left: 64, right: 24, top: 16, bottom: 40 },
      xAxis: { type: "time" as const, axisLabel: { color: colors.secondary, hideOverlap: true } },
      yAxis: {
        type: "category" as const,
        data: ROWS,
        axisLabel: { color: colors.secondary },
      },
      dataZoom: [{ type: "inside" as const, filterMode: "weakFilter" as const }],
      series: [
        {
          type: "custom" as const,
          renderItem,
          encode: { x: [0, 1], y: 2 },
          data: [...segmentItems, ...splitItems],
        },
      ],
    };
  }, [boundaries, colors, segments]);

  return <EChart option={option} height={160} />;
}
