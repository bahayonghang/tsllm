import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Schemas } from "../../src/api/client";
import { mockFetch, renderRoute } from "../helpers";

function column(runId: string, name: string, dataset: string): Schemas["CompareColumnOut"] {
  return {
    run_id: runId,
    name,
    dataset,
    task: "forecast",
    backbone: "model-a",
    mode: "zero_shot",
    state: "succeeded",
    context_length: 16,
    horizon: 4,
  };
}

const compare: Schemas["CompareOut"] = {
  columns: [column("r1", "run one", "ds-one"), column("r2", "run two", "ds-two")],
  rows: [
    { split: "test", metric: "mae_norm_macro", values: { r1: 0.25, r2: null } },
    { split: "val", metric: "mae_norm_macro", values: { r1: 0.5, r2: 0.75 } },
  ],
  warnings: [
    { code: "DATASET_MISMATCH", message: "运行使用了不同的数据集" },
    { code: "ORIGIN_SET_MISMATCH", message: "test 划分的评价起点集合不同" },
  ],
};

describe("ComparePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows every comparability warning and null values as —", async () => {
    const fetchMock = mockFetch({ "/api/runs": [], "/api/compare": compare });
    renderRoute("/compare?run_ids=r1,r2");

    expect(await screen.findByText("运行使用了不同的数据集")).toBeTruthy();
    expect(screen.getByText("test 划分的评价起点集合不同")).toBeTruthy();
    const alerts = screen.getAllByRole("alert");
    expect(alerts.length).toBeGreaterThanOrEqual(2);

    const compareCall = fetchMock.mock.calls
      .map(([input]) => new URL(input instanceof Request ? input.url : String(input)))
      .find((url) => url.pathname === "/api/compare");
    expect(compareCall?.searchParams.get("run_ids")).toBe("r1,r2");

    expect(screen.getAllByText("run one").length).toBeGreaterThan(0);
    expect(screen.getByText("0.25")).toBeTruthy();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
