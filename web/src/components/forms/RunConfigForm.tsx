import { generateForm } from "@rjsf/antd";
import type { ErrorSchema, RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { useMemo } from "react";
import type { Schemas } from "../../api/client";
import {
  allowedModes,
  type FormValue,
  stringAt,
  withAllowedModes,
  withBackboneOptions,
  withChoices,
  withValue,
} from "./schemaTransforms";

const Form = generateForm<FormValue>();

type Props = {
  baseSchema: RJSFSchema;
  optionSchemas: Record<string, RJSFSchema>;
  backbones: Schemas["BackboneInfo"][];
  datasetIds: string[];
  formData: FormValue;
  extraErrors?: ErrorSchema;
  submitText: string;
  onChange: (value: FormValue) => void;
  onSubmit: (value: FormValue) => void;
};

export function RunConfigForm({
  baseSchema,
  optionSchemas,
  backbones,
  datasetIds,
  formData,
  extraErrors,
  submitText,
  onChange,
  onSubmit,
}: Props) {
  const backboneName = stringAt(formData, ["backbone", "name"]);
  const taskType = stringAt(formData, ["task", "type"]);
  const capabilities = backbones.find((item) => item.name === backboneName)?.capabilities;

  const schema = useMemo(() => {
    let next = withChoices(baseSchema, ["dataset"], datasetIds);
    next = withChoices(
      next,
      ["backbone", "name"],
      backbones.map((item) => item.name),
    );
    next = withBackboneOptions(next, backboneName ? optionSchemas[backboneName] : undefined);
    return withAllowedModes(next, capabilities, taskType);
  }, [backboneName, backbones, baseSchema, capabilities, datasetIds, optionSchemas, taskType]);

  const uiSchema = useMemo<UiSchema>(
    () => ({
      backbone: {
        name: {
          "ui:enumDisabled": backbones.filter((item) => !item.installed).map((item) => item.name),
          "ui:enumNames": backbones.map((item) =>
            item.installed ? item.name : `${item.name}（未安装：${item.requires.join("、")}）`,
          ),
        },
      },
      notes: { "ui:widget": "textarea" },
      "ui:submitButtonOptions": { submitText },
    }),
    [backbones, submitText],
  );

  const handleChange = (value: FormValue | undefined) => {
    let next = value ?? {};
    const nextBackbone = stringAt(next, ["backbone", "name"]);
    if (nextBackbone !== backboneName) {
      // Options of the previous backbone do not fit the new Options schema.
      next = withValue(next, ["backbone", "options"], {});
    }
    const modes = allowedModes(
      backbones.find((item) => item.name === nextBackbone)?.capabilities,
      stringAt(next, ["task", "type"]),
    );
    const mode = stringAt(next, ["mode"]);
    if (
      modes !== undefined &&
      (modes.length === 1 || (mode !== undefined && !modes.includes(mode)))
    ) {
      next = withValue(next, ["mode"], modes[0]);
    }
    onChange(next);
  };

  return (
    <Form
      // rjsf keeps its state when a parent changes the schema during a user change,
      // so the form mounts again when the backbone or task type changes the schema.
      key={`${backboneName ?? ""}|${taskType ?? ""}`}
      schema={schema}
      uiSchema={uiSchema}
      formData={formData}
      validator={validator}
      extraErrors={extraErrors}
      showErrorList={false}
      noHtml5Validate
      experimental_defaultFormStateBehavior={{ arrayMinItems: { populate: "requiredOnly" } }}
      onChange={(event) => handleChange(event.formData)}
      onSubmit={(event) => onSubmit(event.formData ?? {})}
    />
  );
}
