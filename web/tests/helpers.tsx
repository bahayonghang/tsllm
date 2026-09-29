import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { App as AntApp } from "antd";
import type { ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import { routes } from "../src/router";

export function newQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

export function withQueryClient(client: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

/** Render the app routes at `url` with a fresh query cache. */
export function renderRoute(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] });
  return render(
    <QueryClientProvider client={newQueryClient()}>
      <AntApp>
        <RouterProvider router={router} />
      </AntApp>
    </QueryClientProvider>,
  );
}

type Handler = (url: URL, request: Request) => unknown;

/** Replace `fetch` with JSON responses from `routes` (path → body or handler). */
export function mockFetch(routes: Record<string, unknown | Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const request = input instanceof Request ? input : new Request(String(input));
    const url = new URL(request.url);
    const route = routes[url.pathname];
    if (route === undefined) {
      return new Response(
        JSON.stringify({
          error: { code: "NOT_FOUND", message: url.pathname, detail: null },
        }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    }
    const body = typeof route === "function" ? route(url, request) : route;
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
