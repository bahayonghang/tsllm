import createClient from "openapi-fetch";
import { isRecord } from "../utils/guards";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

export const api = createClient<paths>({
  // An absolute origin keeps `new Request()` valid in every runtime; paths stay relative.
  baseUrl: globalThis.location?.origin ?? "",
  // Resolve fetch per call so that tests can replace it.
  fetch: (request) => globalThis.fetch(request),
});

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: unknown;

  constructor(status: number, code: string, message: string, detail: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

/** Convert a non-2xx body to ApiError. The service sends `{"error": {code, message, detail}}`. */
export function toApiError(status: number, body: unknown): ApiError {
  const envelope = isRecord(body) ? body.error : undefined;
  if (isRecord(envelope) && typeof envelope.code === "string") {
    const message = typeof envelope.message === "string" ? envelope.message : envelope.code;
    return new ApiError(status, envelope.code, message, envelope.detail ?? null);
  }
  return new ApiError(status, "HTTP_ERROR", `HTTP ${status}`, body ?? null);
}

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || !response.ok) throw toApiError(response.status, error);
  if (data === undefined) throw new ApiError(response.status, "EMPTY_RESPONSE", "响应为空", null);
  return data;
}
