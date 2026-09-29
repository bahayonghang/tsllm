// Narrowing helpers for API fields that the OpenAPI schema types as free objects
// (metrics.json, dataset meta, prediction rows, JSON Schema documents).

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function recordAt(value: unknown, key: string): Record<string, unknown> | undefined {
  if (!isRecord(value)) return undefined;
  const item = value[key];
  return isRecord(item) ? item : undefined;
}

export function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function stringOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function arrayAt(value: unknown, key: string): unknown[] {
  if (!isRecord(value)) return [];
  const item = value[key];
  return Array.isArray(item) ? item : [];
}

export function pointList(value: unknown): [number, number][] {
  if (!Array.isArray(value)) return [];
  const points: [number, number][] = [];
  for (const item of value) {
    if (Array.isArray(item)) {
      const x = numberOrNull(item[0]);
      const y = numberOrNull(item[1]);
      if (x !== null && y !== null) points.push([x, y]);
    }
  }
  return points;
}

export function numberMatrix(value: unknown): number[][] {
  if (!Array.isArray(value)) return [];
  return value.map((row) => (Array.isArray(row) ? row.map((cell) => numberOrNull(cell) ?? 0) : []));
}
