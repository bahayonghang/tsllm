import type { RJSFSchema } from "@rjsf/utils";
import { describe, expect, it } from "vitest";
import type { Schemas } from "../../../src/api/client";
import {
  isSchema,
  toExtraErrors,
  withAllowedModes,
  withBackboneOptions,
  withChoices,
  withValue,
} from "../../../src/components/forms/schemaTransforms";
import fixture from "../../fixtures/run-config.schema.json";

function baseSchema(): RJSFSchema {
  const value: unknown = structuredClone(fixture);
  if (!isSchema(value)) throw new Error("fixture is not a schema");
  return value;
}

function backboneDef(schema: RJSFSchema): RJSFSchema {
  const def = schema.$defs?.BackboneConfig;
  if (typeof def !== "object") throw new Error("BackboneConfig missing");
  return def;
}

const capabilities: Schemas["Capabilities"] = {
  forecast_modes: ["zero_shot", "lora"],
  embed: true,
  quantiles: true,
  multivariate: "native",
  needs_fit_stats: false,
};

describe("withBackboneOptions", () => {
  it("replaces backbone.options through the $ref and keeps the input unchanged", () => {
    const schema = baseSchema();
    const options: RJSFSchema = {
      type: "object",
      title: "AlphaOptions",
      properties: { alpha_opt: { type: "integer", default: 1 } },
      additionalProperties: false,
    };
    const result = withBackboneOptions(schema, options);
    const replaced = backboneDef(result).properties?.options;
    expect(replaced).toMatchObject({
      properties: { alpha_opt: { type: "integer" } },
      additionalProperties: false,
      title: "Options",
    });
    expect(backboneDef(schema).properties?.options).toMatchObject({
      additionalProperties: true,
    });
  });

  it("returns the input without an options schema", () => {
    const schema = baseSchema();
    expect(withBackboneOptions(schema, undefined)).toBe(schema);
  });
});

describe("withAllowedModes", () => {
  it("keeps only the forecast modes of the backbone", () => {
    const result = withAllowedModes(baseSchema(), capabilities, "forecast");
    const mode = result.properties?.mode;
    expect(typeof mode === "object" ? mode.enum : undefined).toEqual(["zero_shot", "lora"]);
  });

  it("allows only head for a classify task", () => {
    const result = withAllowedModes(baseSchema(), capabilities, "classify");
    const mode = result.properties?.mode;
    expect(typeof mode === "object" ? mode.enum : undefined).toEqual(["head"]);
  });

  it("keeps every mode without capabilities", () => {
    const schema = baseSchema();
    expect(withAllowedModes(schema, undefined, "forecast")).toBe(schema);
  });
});

describe("withChoices", () => {
  it("sets an enum on a nested property", () => {
    const result = withChoices(baseSchema(), ["backbone", "name"], ["a", "b"]);
    expect(backboneDef(result).properties?.name).toMatchObject({
      enum: ["a", "b"],
    });
  });
});

describe("withValue", () => {
  it("sets a nested value without changing the input", () => {
    const data = { backbone: { name: "a", options: { x: 1 } } };
    expect(withValue(data, ["backbone", "options"], {})).toEqual({
      backbone: { name: "a", options: {} },
    });
    expect(data.backbone.options).toEqual({ x: 1 });
  });
});

describe("toExtraErrors", () => {
  it("maps field paths and skips the discriminator tag", () => {
    const formData = {
      task: { type: "forecast", horizon: 0 },
      backbone: { options: {} },
    };
    const detail = [
      {
        loc: ["body", "task", "forecast", "horizon"],
        msg: "too small",
        type: "x",
      },
      { loc: ["body", "backbone", "options", "bad"], msg: "extra", type: "x" },
      { loc: ["body"], msg: "whole body", type: "x" },
    ];
    const { errors, unplaced } = toExtraErrors(detail, formData);
    expect(errors).toMatchObject({
      task: { horizon: { __errors: ["too small"] } },
      backbone: { options: { bad: { __errors: ["extra"] } } },
    });
    expect(unplaced).toEqual(["whole body"]);
  });
});
