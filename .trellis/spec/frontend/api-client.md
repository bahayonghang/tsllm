# API Client

> How the UI calls the backend.

---

## Generated Types

- `web/openapi.json` comes from the service: `uv run tsllm api openapi --out web/openapi.json`.
- `pnpm -C web run gen:api` writes `src/api/schema.d.ts`. Commit both files.
- After a backend route or model change, regenerate both files in the same change. CI check: `git diff --exit-code web/src/api/schema.d.ts` after `gen:api`.
- Do not write a TypeScript interface for an API payload by hand. Use `components["schemas"]["RunDetailOut"]` and similar.

---

## Client and Errors

```ts
// src/api/client.ts (reference pattern)
import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "" });

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public detail: unknown,
  ) {
    super(message);
  }
}
```

- Every non-2xx response has the envelope `{"error": {"code", "message", "detail"}}`. Convert it to `ApiError` in one place.
- Show errors with `components/ErrorAlert.tsx`: the Chinese label for known codes, then `message`.
- For `VALIDATION_ERROR` (422), `detail` is a list of field errors. Map the field paths to the form's `extraErrors`.

---

## TanStack Query

- One hook per endpoint in `api/hooks.ts`. Pages do not call `api.GET` directly.
- Query keys are arrays that start with the resource name: `["runs"]`, `["run", id]`, `["metrics", id]`, `["series", id, params]`.
- Mutations invalidate the affected keys. Example: cancel invalidates `["run", id]` and `["runs"]`.
- Poll `["runs"]` every 3 s only while a run is `queued` or `running`. Stop polling when all runs are in a final state.

---

## SSE

```ts
function useRunEvents(
  runId: string,
  enabled: boolean,
): {
  events: RunEvent[];
  ended: boolean;
  error: string | null;
};
```

- Use the browser `EventSource` on `/api/runs/{id}/events`. The browser sends `Last-Event-ID` when it reconnects.
- When the component mounts again, open the stream with `?from=<last id>` so no event repeats.
- Close the stream on the `end` event.
- Keep at most 5,000 events in memory. Show the count of dropped events.
- On a `stage` or `end` event, invalidate `["run", id]` and `["metrics", id]`.

---

## Dev Proxy and Hosting

- `vite.config.ts` proxies `/api` to `http://127.0.0.1:8000` in dev.
- In production the FastAPI service serves `web/dist`. All API URLs are relative (`/api/...`). Do not put a host name in code.
