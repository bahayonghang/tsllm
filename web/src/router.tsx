import { createBrowserRouter, Navigate } from "react-router";
import { AppLayout } from "./components/AppLayout";
import { loadRoute, RouteLoadError, RouteLoading } from "./components/RouteLoading";

export const routes = [
  {
    path: "/",
    element: <AppLayout />,
    HydrateFallback: RouteLoading,
    children: [
      { index: true, element: <Navigate to="/runs" replace /> },
      {
        path: "datasets",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({
          Component: (await import("./pages/DatasetsPage")).DatasetsPage,
        })),
      },
      {
        path: "datasets/:id",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({
          Component: (await import("./pages/DatasetDetailPage")).DatasetDetailPage,
        })),
      },
      {
        path: "runs",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({ Component: (await import("./pages/RunsPage")).RunsPage })),
      },
      {
        path: "runs/new",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({
          Component: (await import("./pages/RunNewPage")).RunNewPage,
        })),
      },
      {
        path: "runs/:id",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({
          Component: (await import("./pages/RunDetailPage")).RunDetailPage,
        })),
      },
      {
        path: "compare",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({
          Component: (await import("./pages/ComparePage")).ComparePage,
        })),
      },
      {
        path: "system",
        ErrorBoundary: RouteLoadError,
        lazy: loadRoute(async () => ({
          Component: (await import("./pages/SystemPage")).SystemPage,
        })),
      },
    ],
  },
];

export const router = createBrowserRouter(routes);
