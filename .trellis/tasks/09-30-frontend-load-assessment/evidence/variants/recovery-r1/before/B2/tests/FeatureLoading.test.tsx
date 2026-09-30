import { act, cleanup, render, screen } from "@testing-library/react";
import { type ComponentType, lazy } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FeatureLoading } from "../src/components/FeatureLoading";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("feature module boundaries", () => {
  it("shows a pending form module and then its interactive control", async () => {
    let resolve: (value: { default: ComponentType }) => void = () => {};
    const pending = new Promise<{ default: ComponentType }>((done) => {
      resolve = done;
    });
    const Form = lazy(() => pending);
    render(
      <FeatureLoading label="表单">
        <Form />
      </FeatureLoading>,
    );
    expect(screen.getByRole("status").textContent).toContain("正在加载表单");
    await act(async () => {
      resolve({ default: () => <button type="button">预览并提交</button> });
    });
    expect(screen.getByRole("button", { name: "预览并提交" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("contains a failed chart import and recovers with a fresh document boundary", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const Failed = lazy(() => Promise.reject(new Error("Synthetic chart module failure")));
    const view = render(
      <FeatureLoading label="图表">
        <Failed />
      </FeatureLoading>,
    );
    expect(await screen.findByText("图表加载失败")).toBeTruthy();
    expect(screen.getByRole("link", { name: "重新加载页面" })).toBeTruthy();
    view.unmount();
    const Recovered = lazy(async () => ({ default: () => <div>图表已恢复</div> }));
    render(
      <FeatureLoading label="图表">
        <Recovered />
      </FeatureLoading>,
    );
    expect(await screen.findByText("图表已恢复")).toBeTruthy();
  });
});
