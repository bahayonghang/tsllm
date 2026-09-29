import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas, unwrap } from "./client";
import type { operations } from "./schema";

export type Split =
  operations["predictions_api_runs__run_id__predictions_get"]["parameters"]["query"]["split"];
export const PREDICTION_SPLITS: readonly Split[] = ["val", "cal", "test"];

export function isSplit(value: string): value is Split {
  return PREDICTION_SPLITS.some((split) => split === value);
}

export const ACTIVE_STATES: readonly string[] = ["queued", "running"];

export function useSystem() {
  return useQuery({
    queryKey: ["system"],
    queryFn: () => unwrap(api.GET("/api/system")),
  });
}

export function useRunConfigSchema() {
  return useQuery({
    queryKey: ["schema"],
    queryFn: () => unwrap(api.GET("/api/schema/run-config")),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useBackbones() {
  return useQuery({
    queryKey: ["backbones"],
    queryFn: () => unwrap(api.GET("/api/backbones")),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useDatasets() {
  return useQuery({
    queryKey: ["datasets"],
    queryFn: () => unwrap(api.GET("/api/datasets")),
  });
}

export function useDataset(datasetId: string) {
  return useQuery({
    queryKey: ["dataset", datasetId],
    queryFn: () =>
      unwrap(
        api.GET("/api/datasets/{dataset_id}", {
          params: { path: { dataset_id: datasetId } },
        }),
      ),
  });
}

export type SeriesParams = {
  channels: string[];
  start?: string;
  end?: string;
  maxPoints?: number;
};

export function useSeries(datasetId: string, params: SeriesParams, enabled = true) {
  return useQuery({
    queryKey: ["series", datasetId, params],
    queryFn: () =>
      unwrap(
        api.GET("/api/datasets/{dataset_id}/series", {
          params: {
            path: { dataset_id: datasetId },
            query: {
              channels: params.channels,
              start: params.start ?? null,
              end: params.end ?? null,
              max_points: params.maxPoints ?? 2000,
            },
          },
        }),
      ),
    enabled: enabled && params.channels.length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useIngest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (datasetId: string) =>
      unwrap(
        api.POST("/api/datasets/{dataset_id}/ingest", {
          params: { path: { dataset_id: datasetId } },
        }),
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["runs"] });
      void client.invalidateQueries({ queryKey: ["datasets"] });
    },
  });
}

export function usePutChannels(datasetId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (channels: Schemas["ChannelSpec"][]) =>
      unwrap(
        api.PUT("/api/datasets/{dataset_id}/channels", {
          params: { path: { dataset_id: datasetId } },
          body: { channels },
        }),
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["dataset", datasetId] });
      void client.invalidateQueries({ queryKey: ["datasets"] });
    },
  });
}

export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => unwrap(api.GET("/api/runs")),
    refetchInterval: (query) =>
      query.state.data?.some((run) => ACTIVE_STATES.includes(run.state)) ? 3000 : false,
  });
}

export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () =>
      unwrap(
        api.GET("/api/runs/{run_id}", {
          params: { path: { run_id: runId ?? "" } },
        }),
      ),
    enabled: runId !== null,
  });
}

export function useSubmitRun() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (config: Schemas["RunConfig"]) => unwrap(api.POST("/api/runs", { body: config })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

export function useCancelRun(runId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/runs/{run_id}/cancel", {
          params: { path: { run_id: runId } },
        }),
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["run", runId] });
      void client.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

export function useMetrics(runId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["metrics", runId],
    queryFn: () =>
      unwrap(
        api.GET("/api/runs/{run_id}/metrics", {
          params: { path: { run_id: runId } },
        }),
      ),
    enabled,
  });
}

export function usePredictionOrigins(runId: string, split: Split | null) {
  const params = { split: split ?? "test", limit: 500 };
  return useQuery({
    queryKey: ["predictions", runId, params],
    queryFn: () =>
      unwrap(
        api.GET("/api/runs/{run_id}/predictions", {
          params: { path: { run_id: runId }, query: params },
        }),
      ),
    enabled: split !== null,
  });
}

export function usePredictionRows(
  runId: string,
  split: Split | null,
  channel: string | null,
  originTime: string | null,
) {
  const params = { split: split ?? "test", channel, origin_time: originTime };
  return useQuery({
    queryKey: ["predictions", runId, params],
    queryFn: () =>
      unwrap(
        api.GET("/api/runs/{run_id}/predictions", {
          params: { path: { run_id: runId }, query: params },
        }),
      ),
    enabled: split !== null && originTime !== null,
  });
}

export function useCompare(runIds: string[]) {
  return useQuery({
    queryKey: ["compare", runIds],
    queryFn: () =>
      unwrap(
        api.GET("/api/compare", {
          params: { query: { run_ids: runIds.join(",") } },
        }),
      ),
    enabled: runIds.length > 0,
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: () => unwrap(api.GET("/api/run-templates")),
  });
}

export function useTemplate(name: string | null) {
  return useQuery({
    queryKey: ["template", name],
    queryFn: () =>
      unwrap(
        api.GET("/api/run-templates/{name}", {
          params: { path: { name: name ?? "" } },
        }),
      ),
    enabled: name !== null,
  });
}

export function useSaveTemplate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ name, config }: { name: string; config: Schemas["RunConfig"] }) =>
      unwrap(
        api.PUT("/api/run-templates/{name}", {
          params: { path: { name } },
          body: config,
        }),
      ),
    onSuccess: (_data, { name }) => {
      void client.invalidateQueries({ queryKey: ["templates"] });
      void client.invalidateQueries({ queryKey: ["template", name] });
    },
  });
}

/** Run detail as openapi-fetch returns it (response types, not request types). */
export type RunDetail = NonNullable<ReturnType<typeof useRun>["data"]>;
