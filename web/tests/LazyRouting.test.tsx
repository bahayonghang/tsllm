import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { App } from "antd";
import type { ComponentType } from "react";
import { createMemoryRouter, type RouteObject, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { loadRoute } from "../src/components/RouteLoading";
import { routes } from "../src/router";
import { mockFetch, newQueryClient } from "./helpers";

type Module = { Component: ComponentType };
const originalUrl = window.location.href;
const mounted: {
  router: ReturnType<typeof createMemoryRouter>;
  client: ReturnType<typeof newQueryClient>;
}[] = [];

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

function mount(initial: string, definitions: RouteObject[] = routes) {
  const router = createMemoryRouter(definitions, { initialEntries: [initial] });
  const client = newQueryClient();
  const view = render(
    <QueryClientProvider client={client}>
      <App>
        <RouterProvider router={router} />
      </App>
    </QueryClientProvider>,
  );
  const result = { router, client, ...view };
  mounted.push(result);
  return result;
}

afterEach(() => {
  cleanup();
  for (const view of mounted.splice(0)) {
    view.router.dispose();
    view.client.clear();
  }
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.history.replaceState({}, "", originalUrl);
});

describe("route module boundaries", () => {
  it("replaces the root entry with the existing runs redirect", async () => {
    mockFetch({ "/api/runs": [] });
    const view = mount("/");
    expect(await screen.findByRole("heading", { name: "运行" })).toBeTruthy();
    expect(view.router.state.location.pathname).toBe("/runs");
    expect(view.router.state.historyAction).toBe("REPLACE");
  });

  it("shows initial loading until the requested page module resolves", async () => {
    mockFetch({ "/api/runs": [] });
    const pending = delayedModule();
    mount(
      "/runs",
      configured("runs", () => pending.promise),
    );
    expect(screen.getByRole("status").textContent).toContain("正在加载页面");
    await act(async () => {
      pending.resolve({ Component: (await import("../src/pages/RunsPage")).RunsPage });
    });
    expect(await screen.findByRole("heading", { name: "运行" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("keeps the layout and shows loading during a menu navigation", async () => {
    mockFetch({ "/api/runs": [], "/api/datasets": [] });
    const pending = delayedModule();
    const view = mount(
      "/runs",
      configured("datasets", () => pending.promise),
    );
    await screen.findByRole("heading", { name: "运行" });
    fireEvent.click(screen.getByRole("link", { name: "数据集" }));
    expect(screen.getByRole("status").textContent).toContain("正在加载页面");
    expect(screen.getByRole("link", { name: "TSFM 实验平台" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "运行" })).toBeTruthy();
    await act(async () => {
      pending.resolve({ Component: (await import("../src/pages/DatasetsPage")).DatasetsPage });
    });
    expect(await screen.findByRole("heading", { name: "数据集" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
    expect(view.router.state.location.pathname).toBe("/datasets");
  });

  it.each(["", "#restore"])(
    "clicks recovery after an initial import failure and preserves query and hash %s",
    async (hash) => {
      const url = `/runs?state=succeeded${hash}`;
      window.history.replaceState({}, "", url);
      const href = window.location.href;
      const reload = vi.fn();
      vi.stubGlobal("location", { ...window.location, reload });
      const pending = delayedModule();
      const view = mount(
        url,
        configured("runs", () => pending.promise),
      );
      await act(async () => {
        pending.reject(new Error("Synthetic module download failure"));
      });
      expect(await screen.findByText("页面加载失败")).toBeTruthy();
      expect(screen.queryByRole("status")).toBeNull();
      const recovery = screen.getByRole("link", { name: "重新加载页面" });
      expect(recovery.getAttribute("href")).toBe(url);
      expect(fireEvent.click(recovery)).toBe(false);
      expect(reload).toHaveBeenCalledTimes(1);
      const location = view.router.state.location;
      expect(location.pathname + location.search + location.hash).toBe(url);
      expect(globalThis.location.href).toBe(href);
    },
  );

  it("shows a failed navigation in the layout with the destination recovery URL", async () => {
    mockFetch({ "/api/runs": [] });
    const pending = delayedModule();
    const view = mount(
      "/runs",
      configured("system", () => pending.promise),
    );
    await screen.findByRole("heading", { name: "运行" });
    const url = "/system?view=versions#restore";
    let navigation: Promise<void> | undefined;
    await act(async () => {
      navigation = view.router.navigate(url);
    });
    expect(screen.getByRole("status").textContent).toContain("正在加载页面");
    await act(async () => {
      pending.reject(new Error("Synthetic module download failure"));
      await navigation;
    });
    expect(await screen.findByText("页面加载失败")).toBeTruthy();
    expect(screen.getByRole("link", { name: "TSFM 实验平台" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByRole("link", { name: "重新加载页面" }).getAttribute("href")).toBe(url);
    const location = view.router.state.location;
    expect(location.pathname + location.search + location.hash).toBe(url);
  });
});
