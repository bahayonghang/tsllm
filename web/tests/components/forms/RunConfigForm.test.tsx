import type { RJSFSchema } from "@rjsf/utils";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { Schemas } from "../../../src/api/client";
import { RunConfigForm } from "../../../src/components/forms/RunConfigForm";
import { type FormValue, isSchema } from "../../../src/components/forms/schemaTransforms";
import fixture from "../../fixtures/run-config.schema.json";

const base: unknown = structuredClone(fixture);
if (!isSchema(base)) throw new Error("fixture is not a schema");

function backbone(
  name: string,
  modes: Schemas["Capabilities"]["forecast_modes"],
  installed = true,
): Schemas["BackboneInfo"] {
  return {
    name,
    capabilities: {
      forecast_modes: modes,
      embed: true,
      quantiles: false,
      multivariate: "native",
      needs_fit_stats: false,
    },
    options_schema: {},
    requires: installed ? [] : ["pkg-x"],
    installed,
    default_checkpoint: null,
    license: null,
    license_url: null,
  };
}

const backbones = [
  backbone("alpha", ["zero_shot", "lora", "full"]),
  backbone("beta", ["zero_shot"]),
  backbone("gamma", ["zero_shot"], false),
];

const optionSchemas: Record<string, RJSFSchema> = {
  alpha: {
    type: "object",
    properties: { alpha_depth: { type: "integer", title: "Alpha Depth", default: 2 } },
    additionalProperties: false,
  },
  beta: {
    type: "object",
    properties: { beta_rate: { type: "number", title: "Beta Rate", default: 0.5 } },
    additionalProperties: false,
  },
  gamma: { type: "object", properties: {}, additionalProperties: false },
};

function Harness({ initial }: { initial: FormValue }) {
  const [formData, setFormData] = useState<FormValue>(initial);
  return (
    <>
      <RunConfigForm
        baseSchema={isSchema(base) ? base : {}}
        optionSchemas={optionSchemas}
        backbones={backbones}
        datasetIds={["ds-one", "ds-two"]}
        formData={formData}
        submitText="提交"
        onChange={setFormData}
        onSubmit={() => {}}
      />
      <output data-testid="state">{JSON.stringify(formData)}</output>
    </>
  );
}

const initial: FormValue = {
  name: "t1",
  dataset: "ds-one",
  task: { type: "forecast", context_length: 16, horizon: 4 },
  backbone: { name: "alpha", options: { alpha_depth: 3 } },
  mode: "lora",
};

function selectById(id: string): HTMLElement {
  const box = screen.getAllByRole("combobox").find((element) => element.id === id);
  if (!box) throw new Error(`combobox ${id} not found`);
  return box;
}

async function openOptions(id: string): Promise<string[]> {
  fireEvent.mouseDown(selectById(id));
  const listbox = await screen
    .findByRole("listbox", { hidden: true }, { timeout: 2000 })
    .catch(() => null);
  const scope = listbox?.parentElement ?? document.body;
  return within(scope)
    .getAllByRole("option", { hidden: true })
    .map((option) => option.getAttribute("aria-label") ?? option.textContent ?? "")
    .filter((label) => label !== "");
}

describe("RunConfigForm", () => {
  it("switches the Options fields when the backbone changes", async () => {
    render(<Harness initial={initial} />);
    expect(screen.getByText("Alpha Depth")).toBeTruthy();
    expect(screen.queryByText("Beta Rate")).toBeNull();

    fireEvent.mouseDown(selectById("root_backbone_name"));
    fireEvent.click(await screen.findByTitle("beta"));

    await waitFor(() => expect(screen.getByText("Beta Rate")).toBeTruthy());
    expect(screen.queryByText("Alpha Depth")).toBeNull();
    const state = JSON.parse(screen.getByTestId("state").textContent ?? "{}");
    expect(state.backbone.options).not.toHaveProperty("alpha_depth");
    // lora is not supported by the new backbone, so the form falls back to an allowed mode.
    expect(state.mode).toBe("zero_shot");
  });

  it("offers only the modes that the backbone supports", async () => {
    render(<Harness initial={{ ...initial, backbone: { name: "beta", options: {} } }} />);
    const modes = await openOptions("root_mode");
    expect(modes).toContain("zero_shot");
    expect(modes).not.toContain("lora");
    expect(modes).not.toContain("full");
  });

  it("fixes the mode to head for a classify task", async () => {
    render(
      <Harness
        initial={{
          ...initial,
          task: { type: "classify", context_length: 16 },
          mode: "head",
        }}
      />,
    );
    const modes = await openOptions("root_mode");
    expect(modes).toEqual(["head"]);
  });

  it("disables a backbone that is not installed", async () => {
    render(<Harness initial={initial} />);
    fireEvent.mouseDown(selectById("root_backbone_name"));
    const option = await screen.findByTitle("gamma（未安装：pkg-x）");
    expect(option.getAttribute("aria-disabled") ?? option.className).toMatch(/true|disabled/);
  });
});
