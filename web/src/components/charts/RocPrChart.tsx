import { Col, Row, Typography } from "antd";
import { useMemo } from "react";
import { EChart, seriesColor, useChartColors } from "./EChart";

type Curves = Record<string, [number, number][]>;

type Props = {
  /** Split → `[fpr, tpr]` points. */
  roc: Curves;
  /** Split → `[recall, precision]` points. */
  pr: Curves;
};

function useCurveOption(curves: Curves, xName: string, yName: string) {
  const colors = useChartColors();
  return useMemo(
    () => ({
      tooltip: { trigger: "axis" as const },
      legend: { top: 0, textStyle: { color: colors.text } },
      grid: { left: 56, right: 24, top: 40, bottom: 48 },
      xAxis: {
        type: "value" as const,
        min: 0,
        max: 1,
        name: xName,
        nameLocation: "middle" as const,
        nameGap: 28,
        axisLabel: { color: colors.secondary },
      },
      yAxis: {
        type: "value" as const,
        min: 0,
        max: 1,
        name: yName,
        axisLabel: { color: colors.secondary },
        splitLine: { lineStyle: { color: colors.border } },
      },
      series: Object.entries(curves).map(([split, points], index) => ({
        name: split,
        type: "line" as const,
        showSymbol: false,
        color: seriesColor(colors.series, index),
        data: points,
      })),
    }),
    [colors, curves, xName, yName],
  );
}

export function RocPrChart({ roc, pr }: Props) {
  const rocOption = useCurveOption(roc, "假正率", "真正率");
  const prOption = useCurveOption(pr, "召回率", "精确率");
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} md={12}>
        <Typography.Text strong>ROC 曲线</Typography.Text>
        <EChart option={rocOption} height={320} />
      </Col>
      <Col xs={24} md={12}>
        <Typography.Text strong>PR 曲线</Typography.Text>
        <EChart option={prOption} height={320} />
      </Col>
    </Row>
  );
}
