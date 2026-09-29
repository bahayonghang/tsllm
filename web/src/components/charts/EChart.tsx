import { theme } from "antd";
import type { EChartsOption } from "echarts";
import { BarChart, CustomChart, LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/esm/core";
import { useMemo } from "react";

echarts.use([
  LineChart,
  BarChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
  MarkLineComponent,
  CanvasRenderer,
]);

export type ChartOption = EChartsOption;

type Props = {
  option: ChartOption;
  height?: number;
  onEvents?: Record<string, (params: unknown) => void>;
};

export function EChart({ option, height = 320, onEvents }: Props) {
  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      onEvents={onEvents}
      style={{ height, width: "100%" }}
    />
  );
}

/** Chart colors from the antd theme, so that a dark theme stays readable. */
export function useChartColors() {
  const { token } = theme.useToken();
  return useMemo(
    () => ({
      text: token.colorText,
      secondary: token.colorTextSecondary,
      border: token.colorBorderSecondary,
      series: [
        token.colorPrimary,
        token.colorSuccess,
        token.colorWarning,
        token.colorError,
        token.purple,
        token.cyan,
        token.magenta,
        token.gold,
      ],
    }),
    [token],
  );
}

export function seriesColor(colors: string[], index: number): string {
  return colors[index % colors.length] ?? "#888";
}
