import { type ErrorSchema, ErrorSchemaBuilder, type RJSFSchema } from "@rjsf/utils";
import type { Schemas } from "../../api/client";
import { isRecord } from "../../utils/guards";

export type FormValue = Record<string, unknown>;

type Definition = NonNullable<RJSFSchema["properties"]>[string];

export function isSchema(value: unknown): value is RJSFSchema {
  return isRecord(value);
}

/** Follow one local `#/$defs/<name>` reference from the root schema. */
function resolve(root: RJSFSchema, node: Definition | undefined): RJSFSchema | undefined {
  if (typeof node !== "object") return undefined;
  const ref = node.$ref;
  if (ref?.startsWith("#/$defs/")) {
    const target = root.$defs?.[ref.slice("#/$defs/".length)];
    return typeof target === "object" ? target : undefined;
  }
  return node;
}

/** The schema object of a property path, inside the given (already cloned) root. */
function propertyAt(root: RJSFSchema, path: string[]): RJSFSchema | undefined {
  let node: RJSFSchema | undefined = root;
  for (const key of path) {
    node = node ? resolve(root, node.properties?.[key]) : undefined;
  }
  return node;
}

/** Replace `backbone.options` with the Options schema of the selected backbone. */
export function withBackboneOptions(
  schema: RJSFSchema,
  optionsSchema: RJSFSchema | undefined,
): RJSFSchema {
  if (optionsSchema === undefined) return schema;
  const root = structuredClone(schema);
  const backbone = propertyAt(root, ["backbone"]);
  const current = backbone?.properties?.options;
  if (backbone?.properties === undefined || typeof current !== "object") return schema;
  backbone.properties.options = {
    ...structuredClone(optionsSchema),
    title: current.title,
    description: current.description,
  };
  return root;
}

/** Modes that a backbone supports for a task type. A classify task allows only `head`. */
export function allowedModes(
  capabilities: Schemas["Capabilities"] | undefined,
  taskType: string | undefined,
): string[] | undefined {
  if (taskType === "classify") return ["head"];
  return capabilities?.forecast_modes;
}

/** Keep only the allowed `mode` values in the enum. Without capabilities all values stay. */
export function withAllowedModes(
  schema: RJSFSchema,
  capabilities: Schemas["Capabilities"] | undefined,
  taskType: string | undefined,
): RJSFSchema {
  const allowed = allowedModes(capabilities, taskType);
  if (allowed === undefined) return schema;
  const root = structuredClone(schema);
  const mode = propertyAt(root, ["mode"]);
  if (mode?.enum === undefined) return schema;
  mode.enum = mode.enum.filter((value) => typeof value === "string" && allowed.includes(value));
  return root;
}

/** Turn a string property into a dropdown with the given values. */
export function withChoices(schema: RJSFSchema, path: string[], values: string[]): RJSFSchema {
  if (values.length === 0) return schema;
  const root = structuredClone(schema);
  const target = propertyAt(root, path);
  if (target === undefined) return schema;
  target.enum = [...values];
  return root;
}

export function valueAt(data: unknown, path: string[]): unknown {
  let node = data;
  for (const key of path) {
    node = isRecord(node) ? node[key] : undefined;
  }
  return node;
}

export function stringAt(data: unknown, path: string[]): string | undefined {
  const value = valueAt(data, path);
  return typeof value === "string" ? value : undefined;
}

export function withValue(data: FormValue, path: string[], value: unknown): FormValue {
  const [head, ...rest] = path;
  if (head === undefined) return data;
  if (rest.length === 0) return { ...data, [head]: value };
  const child = data[head];
  return {
    ...data,
    [head]: withValue(isRecord(child) ? child : {}, rest, value),
  };
}

/**
 * Map the field errors of a 422 `VALIDATION_ERROR` to rjsf `extraErrors`.
 * Pydantic adds the discriminator tag of a union (for example `task.forecast.horizon`);
 * a segment equal to the `type` value of the current object is skipped.
 */
export function toExtraErrors(
  detail: unknown,
  formData: unknown,
): { errors: ErrorSchema | undefined; unplaced: string[] } {
  const builder = new ErrorSchemaBuilder();
  const unplaced: string[] = [];
  let placed = 0;
  for (const item of Array.isArray(detail) ? detail : []) {
    if (!isRecord(item) || !Array.isArray(item.loc)) continue;
    const message = typeof item.msg === "string" ? item.msg : "字段错误";
    const loc = item.loc.map(String);
    if (loc[0] === "body") loc.shift();
    const path: string[] = [];
    let node: unknown = formData;
    for (const segment of loc) {
      if (isRecord(node) && !(segment in node) && node.type === segment) continue;
      path.push(segment);
      node = isRecord(node)
        ? node[segment]
        : Array.isArray(node)
          ? node[Number(segment)]
          : undefined;
    }
    if (path.length === 0) {
      unplaced.push(message);
    } else {
      builder.addErrors(message, path);
      placed += 1;
    }
  }
  return { errors: placed > 0 ? builder.ErrorSchema : undefined, unplaced };
}
