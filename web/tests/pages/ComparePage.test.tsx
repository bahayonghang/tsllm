import { fireEvent, screen, within } from "@testing-library/react";
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
    { code: "DATASET_MISMATCH", message: "runs have different dataset values" },
    {
      code: "ORIGIN_SET_MISMATCH",
      message: "runs have different origin sets in split 'test'",
      split: "test",
    },
  ],
};

describe("ComparePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows every comparability warning and null values as —", async () => {
    const fetchMock = mockFetch({ "/api/runs": [], "/api/compare": compare });
    renderRoute("/compare?run_ids=r1,r2");

    expect(await screen.findByText("所选运行使用了不同的数据集")).toBeTruthy();
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

  it("shows all known codes in Chinese with separate run and split context", async () => {
    const payload: Schemas["CompareOut"] = {
      ...compare,
      columns: [
        { ...column("r1", "shared name", "ds-one"), state: "failed" },
        { ...column("r2", "shared name", "ds-two"), state: "cancelled" },
        ingestColumn,
      ],
      warnings: [
        { code: "RUN_NOT_SUCCEEDED", message: "run 'r1' state is 'failed'", run_id: "r1" },
        { code: "RUN_NOT_SUCCEEDED", message: "run 'r2' state is 'cancelled'", run_id: "r2" },
        ...compare.warnings,
        { code: "TASK_MISMATCH", message: "runs have different task values" },
        { code: "CONTEXT_LENGTH_MISMATCH", message: "runs have different context_length values" },
        { code: "HORIZON_MISMATCH", message: "runs have different horizon values" },
        {
          code: "ORIGIN_SET_MISMATCH",
          message: "runs have different origin sets in split 'val'",
          split: "val",
        },
        ingestWarning,
      ],
    };
    mockFetch({ "/api/runs": [], "/api/compare": payload });
    renderRoute("/compare?run_ids=r1,r2,i1");

    expect(await screen.findAllByText("运行尚未成功，当前结果可能不完整")).toHaveLength(2);
    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(payload.warnings.length);
    expect(within(alerts[0] as HTMLElement).getByText("运行：shared name（r1）")).toBeTruthy();
    expect(within(alerts[0] as HTMLElement).getByText("失败")).toBeTruthy();
    expect(within(alerts[1] as HTMLElement).getByText("运行：shared name（r2）")).toBeTruthy();
    expect(within(alerts[1] as HTMLElement).getByText("已取消")).toBeTruthy();
    for (const title of [
      "所选运行使用了不同的数据集",
      "所选运行的任务类型不同",
      "所选运行的上下文长度不同",
      "所选运行的预测步长不同",
      "test 划分的评价起点集合不同",
      "val 划分的评价起点集合不同",
      "入库作业没有实验指标；结果保留该作业，指标显示为空",
    ]) {
      expect(screen.getByText(title)).toBeTruthy();
    }
    expect(screen.getByText("运行：ingest job（i1）")).toBeTruthy();
  });

  it("retains legacy, null-context, unknown, and missing-column warning details", async () => {
    const warnings: Schemas["CompareWarningOut"][] = [
      { code: "RUN_NOT_SUCCEEDED", message: "run 'r1' state is 'failed'" },
      { code: "ORIGIN_SET_MISMATCH", message: "legacy origin details", split: null },
      { code: "NON_EXPERIMENT_RUN", message: "legacy ingest details", run_id: null },
      { code: "RUN_NOT_SUCCEEDED", message: "missing column details", run_id: "missing" },
      { code: "NEW_COMPARE_RULE", message: "new server rule" },
      { code: "toString", message: "unknown reserved name" },
    ];
    mockFetch({ "/api/runs": [], "/api/compare": { ...compare, warnings } });
    renderRoute("/compare?run_ids=r1,r2");

    expect(await screen.findAllByText("运行尚未成功，当前结果可能不完整")).toHaveLength(2);
    expect(screen.getByText("运行的评价起点集合不同")).toBeTruthy();
    expect(screen.getAllByText("服务返回了对比警告")).toHaveLength(2);
    expect(screen.getByText("运行：missing")).toBeTruthy();
    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(warnings.length);
    warnings.forEach((warning, index) => {
      const alert = alerts[index];
      expect(alert?.textContent).toContain(warning.code);
      expect(alert?.textContent).toContain(warning.message);
    });
    expect(within(alerts[0] as HTMLElement).queryByText(/运行：/)).toBeNull();
  });

  it("preserves repeated identical warnings without duplicate React keys", async () => {
    const consoleError = vi.spyOn(console, "error");
    const warning = { code: "DATASET_MISMATCH", message: "runs have different dataset values" };
    mockFetch({ "/api/runs": [], "/api/compare": { ...compare, warnings: [warning, warning] } });
    renderRoute("/compare?run_ids=r1,r2");
    expect(await screen.findAllByText("所选运行使用了不同的数据集")).toHaveLength(2);
    expect(screen.getAllByRole("alert")).toHaveLength(2);
    expect(consoleError.mock.calls.flat().join(" ")).not.toContain("same key");
  });

  it("keeps a manual mixed URL and excludes ingest jobs from selection options", async () => {
    const fetchMock = mockFetch({
      "/api/runs": [runSummary(column("r1", "run one", "ds-one")), runSummary(ingestColumn)],
      "/api/compare": {
        columns: [column("r1", "run one", "ds-one"), ingestColumn],
        rows: [{ split: "test", metric: "mae_norm_macro", values: { r1: 0.25, i1: null } }],
        warnings: [ingestWarning],
      } satisfies Schemas["CompareOut"],
    });
    renderRoute("/compare?run_ids=r1,i1");
    expect(
      await screen.findByText("入库作业没有实验指标；结果保留该作业，指标显示为空"),
    ).toBeTruthy();
    const compareCalls = fetchMock.mock.calls
      .map(([input]) => new URL(input instanceof Request ? input.url : String(input)))
      .filter((url) => url.pathname === "/api/compare");
    expect(compareCalls.every((url) => url.searchParams.get("run_ids") === "r1,i1")).toBe(true);
    expect(screen.getByText("0.25")).toBeTruthy();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    const select = screen.getAllByRole("combobox")[0];
    if (!select) throw new Error("Run selector was not rendered");
    fireEvent.mouseDown(select);
    expect((await screen.findAllByText("run one（r1）")).length).toBeGreaterThan(0);
    expect(screen.queryByText("ingest job（i1）")).toBeNull();
  });

  it("shows no warnings for comparable experiments", async () => {
    mockFetch({ "/api/runs": [], "/api/compare": { ...compare, warnings: [] } });
    renderRoute("/compare?run_ids=r1,r2");
    expect(await screen.findByText("0.25")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("renders an ingest-only comparison without metric rows or a chart", async () => {
    mockFetch({
      "/api/runs": [runSummary(ingestColumn)],
      "/api/compare": { columns: [ingestColumn], rows: [], warnings: [ingestWarning] },
    });
    renderRoute("/compare?run_ids=i1");
    expect(
      await screen.findByText("入库作业没有实验指标；结果保留该作业，指标显示为空"),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: "ingest job" })).toBeTruthy();
    expect(screen.queryByText("指标柱状图")).toBeNull();
  });

  it("keeps ingest checkboxes disabled in the run-list comparison entry", async () => {
    mockFetch({
      "/api/runs": [runSummary(column("r1", "run one", "ds-one")), runSummary(ingestColumn)],
    });
    renderRoute("/runs");
    const ingestLink = await screen.findByRole("link", { name: "ingest job" });
    const ingestRow = ingestLink.closest("tr");
    const experimentRow = screen.getByRole("link", { name: "run one" }).closest("tr");
    if (!ingestRow || !experimentRow) throw new Error("Run rows were not rendered");
    expect(within(ingestRow).getByRole("checkbox").hasAttribute("disabled")).toBe(true);
    const experimentCheckbox = within(experimentRow).getByRole("checkbox");
    expect(experimentCheckbox.hasAttribute("disabled")).toBe(false);
    fireEvent.click(experimentCheckbox);
    expect(screen.getByRole("button", { name: "对比所选（1）" }).hasAttribute("disabled")).toBe(
      false,
    );
  });
});

const ingestColumn: Schemas["CompareColumnOut"] = {
  ...column("i1", "ingest job", "ds-one"),
  task: null,
  backbone: null,
  mode: null,
  context_length: null,
  horizon: null,
};
const ingestWarning: Schemas["CompareWarningOut"] = {
  code: "NON_EXPERIMENT_RUN",
  message: "run 'i1' is an ingest job and has no experiment metrics",
  run_id: "i1",
};

function runSummary(item: Schemas["CompareColumnOut"]): Schemas["RunSummary"] {
  return {
    ...item,
    kind: item.task === null ? "ingest" : "experiment",
    created_at: "2026-09-30T00:00:00Z",
    finished_at: "2026-09-30T00:01:00Z",
    primary_metric: null,
    primary_value: null,
  };
}
