import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import { App } from "antd";
import type { ComponentType } from "react";
import { createMemoryRouter, type RouteObject, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { loadRoute } from "../src/components/RouteLoading";
import { routes } from "../src/router";
import { mockFetch, newQueryClient } from "./helpers";

type Module = { Component: ComponentType };

function delayedModule() {
  let resolve: (value: Module) => void = () => {};
  let reject: (error: Error) => void = () => {};
  const promise = new Promise<Module>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function configured(path: string, load: () => Promise<Module>): RouteObject[] {
  return routes.map((route) => ({
    ...route,
    children: route.children.map((child) =>
      child.path === path ? { ...child, lazy: loadRoute(load) } : child,
    ),
  }));
}

function mount(initial: string, definitions: RouteObject[]) {
  const router = createMemoryRouter(definitions, { initialEntries: [initial] });
  const view = render(
    <QueryClientProvider client={newQueryClient()}>
      <App>
        <RouterProvider router={router} />
      </App>
    </QueryClientProvider>,
  );
  return { router, ...view };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("route module boundaries", () => {
  it("shows initial loading until the real page module resolves", async () => {
    mockFetch({ "/api/runs": [] });
    const pending = delayedModule();
    const view = mount(
      "/runs",
      configured("runs", () => pending.promise),
    );
    expect(screen.getByRole("status").textContent).toContain("正在加载页面");
    await act(async () => {
      pending.resolve({ Component: (await import("../src/pages/RunsPage")).RunsPage });
    });
    expect(await screen.findByRole("heading", { name: "运行" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
    view.router.dispose();
  });

  it("shows navigation loading then renders the requested page", async () => {
    mockFetch({ "/api/runs": [], "/api/datasets": [] });
    const pending = delayedModule();
    const view = mount(
      "/runs",
      configured("datasets", () => pending.promise),
    );
    await screen.findByRole("heading", { name: "运行" });
    let navigation: Promise<void> | undefined;
    await act(async () => {
      navigation = view.router.navigate("/datasets");
    });
    expect(screen.getByRole("status").textContent).toContain("正在加载页面");
    await act(async () => {
      pending.resolve({ Component: (await import("../src/pages/DatasetsPage")).DatasetsPage });
      await navigation;
    });
    expect(await screen.findByRole("heading", { name: "数据集" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
    view.router.dispose();
  });

  it("shows module failure with a full-document recovery URL and resolves after reload", async () => {
    mockFetch({ "/api/runs": [] });
    const pending = delayedModule();
    const view = mount(
      "/runs?state=succeeded",
      configured("runs", () => pending.promise),
    );
    await act(async () => {
      pending.reject(new Error("Synthetic module download failure"));
    });
    expect(await screen.findByText("页面加载失败")).toBeTruthy();
    expect(screen.getByRole("link", { name: "重新加载页面" }).getAttribute("href")).toBe(
      "/runs?state=succeeded",
    );
    view.router.dispose();
    view.unmount();
    // A document reload creates a new router and imports the working module.
    const recovered = mount("/runs?state=succeeded", routes);
    expect(await screen.findByRole("heading", { name: "运行" })).toBeTruthy();
    expect(recovered.router.state.errors).toBeNull();
    recovered.router.dispose();
  });
});
