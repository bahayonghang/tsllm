import { isValidElement } from "react";
import { createMemoryRouter, type RouteObject } from "react-router";
import { describe, expect, it } from "vitest";
import { routes } from "../src/router";

const entries = [
  {
    url: "/datasets?sort=name#list",
    path: "datasets",
    component: async () => (await import("../src/pages/DatasetsPage")).DatasetsPage,
  },
  {
    url: "/datasets/synthetic-dataset?channel=signal#series",
    path: "datasets/:id",
    id: "synthetic-dataset",
    component: async () => (await import("../src/pages/DatasetDetailPage")).DatasetDetailPage,
  },
  {
    url: "/runs?state=succeeded#list",
    path: "runs",
    component: async () => (await import("../src/pages/RunsPage")).RunsPage,
  },
  {
    url: "/runs/new?from=synthetic-run#config",
    path: "runs/new",
    component: async () => (await import("../src/pages/RunNewPage")).RunNewPage,
  },
  {
    url: "/runs/synthetic-run?split=test&channel=signal#results",
    path: "runs/:id",
    id: "synthetic-run",
    component: async () => (await import("../src/pages/RunDetailPage")).RunDetailPage,
  },
  {
    url: "/compare?run_ids=first,second&metric=mae#chart",
    path: "compare",
    component: async () => (await import("../src/pages/ComparePage")).ComparePage,
  },
  {
    url: "/system?view=versions#details",
    path: "system",
    component: async () => (await import("../src/pages/SystemPage")).SystemPage,
  },
];

async function initializedRouter(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] });
  if (!router.state.initialized) {
    await new Promise<void>((resolve) => {
      const unsubscribe = router.subscribe((state) => {
        if (state.initialized) {
          unsubscribe();
          resolve();
        }
      });
    });
  }
  return router;
}

function routeComponent(route: RouteObject | undefined) {
  if (route?.Component) return route.Component;
  if (isValidElement(route?.element)) return route.element.type;
  throw new Error("Expected a resolved route component");
}

describe("route loading contract", () => {
  it.each(entries)("loads the expected page at $url and keeps its full URL", async (entry) => {
    const definition = routes[0]?.children.find((child) => child.path === entry.path);
    expect(definition?.lazy).toBeTypeOf("function");
    const router = await initializedRouter(entry.url);
    try {
      expect(router.state.errors).toBeNull();
      const location = router.state.location;
      expect(location.pathname + location.search + location.hash).toBe(entry.url);
      const match = router.state.matches.at(-1);
      expect(match?.route.path).toBe(entry.path);
      expect(match?.params.id).toBe(entry.id);
      expect(routeComponent(match?.route)).toBe(await entry.component());
    } finally {
      router.dispose();
    }
  });

  it("navigates across all seven pages with query parameters and fragments", async () => {
    const router = await initializedRouter("/runs");
    try {
      for (const entry of entries) {
        await router.navigate(entry.url);
        expect(router.state.navigation.state).toBe("idle");
        expect(router.state.errors).toBeNull();
        const location = router.state.location;
        expect(location.pathname + location.search + location.hash).toBe(entry.url);
        expect(routeComponent(router.state.matches.at(-1)?.route)).toBe(await entry.component());
      }
      await router.navigate(-1);
      expect(router.state.location.pathname).toBe("/compare");
      expect(router.state.location.search).toBe("?run_ids=first,second&metric=mae");
      expect(router.state.location.hash).toBe("#chart");
      await router.navigate(1);
      expect(router.state.location.pathname).toBe("/system");
      expect(router.state.location.search).toBe("?view=versions");
      expect(router.state.location.hash).toBe("#details");
    } finally {
      router.dispose();
    }
  });
});
