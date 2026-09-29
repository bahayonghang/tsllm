import { createBrowserRouter, Navigate } from "react-router";
import { AppLayout } from "./components/AppLayout";
import { ComparePage } from "./pages/ComparePage";
import { DatasetDetailPage } from "./pages/DatasetDetailPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunNewPage } from "./pages/RunNewPage";
import { RunsPage } from "./pages/RunsPage";
import { SystemPage } from "./pages/SystemPage";

export const routes = [
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/runs" replace /> },
      { path: "datasets", element: <DatasetsPage /> },
      { path: "datasets/:id", element: <DatasetDetailPage /> },
      { path: "runs", element: <RunsPage /> },
      { path: "runs/new", element: <RunNewPage /> },
      { path: "runs/:id", element: <RunDetailPage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "system", element: <SystemPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
