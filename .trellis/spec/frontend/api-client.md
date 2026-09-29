# API Client

> How the UI calls the backend.

---

## Generated Types

- `web/openapi.json` comes from the service: `uv run tsllm api openapi --out web/openapi.json`.
- `pnpm -C web run gen:api` writes `src/api/schema.d.ts`. Commit both files.
- After a backend route or model change, regenerate both files in the same change. CI check: `git diff --exit-code web/src/api/schema.d.ts` after `gen:api`.
- Do not write a TypeScript interface for an API payload by hand. Use `Schemas["CompareOut"]` (`Schemas = components["schemas"]`, exported by `client.ts`) for request bodies and test fixtures.
- For response data, use the type that a hook returns, for example `RunDetail` in `hooks.ts`: `NonNullable<ReturnType<typeof useRun>["data"]>`. openapi-fetch maps some schema types differently from `components["schemas"]` (a tuple becomes an array), so `Schemas["JobSpec"]` does not match the response of `useRun`.
- Fields that the API types as `unknown` or a free dictionary (`metrics`, dataset `meta`, event `data`) are read with the narrowing helpers in `utils/guards.ts` and the readers in `utils/metrics.ts` and `utils/datasetMeta.ts`. Do not cast them.

---

## Client and Errors

```ts
// src/api/client.ts
export const api = createClient<paths>({
  // An absolute origin keeps `new Request()` valid in every runtime; paths stay relative.
  baseUrl: globalThis.location?.origin ?? "",
  // Resolve fetch per call so that tests can replace it.
  fetch: (request) => globalThis.fetch(request),
});
```

- `toApiError(status, body)` converts the error envelope to `ApiError {status, code, message, detail}`. `unwrap(request)` returns `data` or throws `ApiError`. Every hook calls `unwrap`.

- Every non-2xx response has the envelope `{"error": {"code", "message", "detail"}}`. Convert it to `ApiError` in one place.
- Show errors with `components/ErrorAlert.tsx`: the Chinese label for known codes (`CODE_LABELS`), then `message`, then the field list of `detail`.
- For `VALIDATION_ERROR` (422), `detail` is a list of field errors. `toExtraErrors(detail, formData)` in `schemaTransforms.ts` maps the field paths to the form's `extraErrors`. It skips the discriminator segment of a union in `loc`. Paths that do not match a form field are shown in an `Alert`.

---

## TanStack Query

- One hook per endpoint in `api/hooks.ts`. Pages do not call `api.GET` directly.
- Query keys are arrays that start with the resource name: `["runs"]`, `["run", id]`, `["metrics", id]`, `["series", id, params]`.
- Mutations invalidate the affected keys. Example: cancel invalidates `["run", id]` and `["runs"]`.
- Poll `["runs"]` every 3 s only while a run is `queued` or `running`. Stop polling when all runs are in a final state.
- The run-config schema key is `["schema"]`. Templates use `["templates"]` and `["template", name]`.

---

## SSE

```ts
function useRunEvents(
  runId: string,
  enabled: boolean,
): {
  events: RunEvent[];
  dropped: number;
  ended: boolean;
  error: string | null;
};
```

- Events of each run are kept in a module-level store in `sse.ts`, so a remount continues from the last id. Events with an id at or below the last id are skipped (a browser reconnect resends them).

- Use the browser `EventSource` on `/api/runs/{id}/events`. The browser sends `Last-Event-ID` when it reconnects.
- When the component mounts again, open the stream with `?from=<last id>` so no event repeats.
- Close the stream on the `end` event.
- Keep at most 5,000 events in memory. Show the count of dropped events.
- On a `stage` or `end` event, invalidate `["run", id]` and `["metrics", id]`.
- Render and invalidate at most once per 200 ms (`FLUSH_MS`). A finished run replays its full log at once; one render and one invalidation per event caused about 6 refetches of the same queries. The `end` event flushes at once.

---

## Dev Proxy and Hosting

- `vite.config.ts` proxies `/api` to `http://127.0.0.1:8000` in dev.
- In production the FastAPI service serves `web/dist`. All API URLs are relative (`/api/...`). Do not put a host name in code.
