import type { ErrorSchema, RJSFSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { App, Button, Card, Input, Modal, Select, Space, Typography } from "antd";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { ApiError, type Schemas } from "../api/client";
import {
  useBackbones,
  useDatasets,
  useRun,
  useRunConfigSchema,
  useSaveTemplate,
  useSubmitRun,
  useTemplate,
  useTemplates,
} from "../api/hooks";
import { ErrorAlert } from "../components/ErrorAlert";
import { RunConfigForm } from "../components/forms/RunConfigForm";
import { type FormValue, isSchema, toExtraErrors } from "../components/forms/schemaTransforms";

function isRunConfig(value: FormValue, schema: RJSFSchema): value is Schemas["RunConfig"] {
  return validator.isValid(schema, value, schema);
}

export function RunNewPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchParams, setSearchParams] = useSearchParams();
  const templateName = searchParams.get("template");
  const fromRunId = searchParams.get("from");

  const schemaQuery = useRunConfigSchema();
  const backbones = useBackbones();
  const datasets = useDatasets();
  const templates = useTemplates();
  const template = useTemplate(templateName);
  const fromRun = useRun(fromRunId);
  const submit = useSubmitRun();
  const saveTemplate = useSaveTemplate();

  const [formData, setFormData] = useState<FormValue>({});
  const [extraErrors, setExtraErrors] = useState<ErrorSchema | undefined>();
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [preview, setPreview] = useState<Schemas["RunConfig"] | null>(null);
  const [newTemplateName, setNewTemplateName] = useState("");
  const applied = useRef<string | null>(null);

  // Load a template or a previous run config once per URL parameter value.
  useEffect(() => {
    if (templateName && template.data && applied.current !== `template:${templateName}`) {
      applied.current = `template:${templateName}`;
      setFormData(template.data);
      setExtraErrors(undefined);
    }
  }, [templateName, template.data]);
  useEffect(() => {
    const config = fromRun.data?.job.run;
    if (fromRunId && config && applied.current !== `from:${fromRunId}`) {
      applied.current = `from:${fromRunId}`;
      setFormData(config);
      setExtraErrors(undefined);
    }
  }, [fromRunId, fromRun.data]);

  const document = schemaQuery.data;
  const baseSchema = document?.run_config;
  const optionsDocument = document?.backbone_options;
  const optionSchemas: Record<string, RJSFSchema> = {};
  if (optionsDocument && typeof optionsDocument === "object") {
    for (const [name, value] of Object.entries(optionsDocument)) {
      if (isSchema(value)) optionSchemas[name] = value;
    }
  }

  const handleSubmit = (value: FormValue) => {
    if (!isSchema(baseSchema) || !isRunConfig(value, baseSchema)) {
      void message.error("配置未通过校验");
      return;
    }
    setPreview(value);
  };

  const confirmSubmit = () => {
    if (preview === null) return;
    setSubmitError(null);
    submit.mutate(preview, {
      onSuccess: (result) => {
        setPreview(null);
        navigate(`/runs/${result.run_id}`);
      },
      onError: (error) => {
        setPreview(null);
        if (error instanceof ApiError && error.code === "VALIDATION_ERROR") {
          const mapped = toExtraErrors(error.detail, formData);
          setExtraErrors(mapped.errors);
          if (mapped.unplaced.length > 0 || mapped.errors === undefined) setSubmitError(error);
        } else {
          setSubmitError(error);
        }
      },
    });
  };

  const handleSaveTemplate = () => {
    const name = newTemplateName.trim();
    if (!/^[A-Za-z0-9_-]+$/.test(name)) {
      void message.error("模板名只能包含字母、数字、下划线和连字符");
      return;
    }
    if (!isSchema(baseSchema) || !isRunConfig(formData, baseSchema)) {
      void message.error("配置未通过校验，不能保存为模板");
      return;
    }
    saveTemplate.mutate(
      { name, config: formData },
      {
        onSuccess: () => {
          void message.success(`已保存模板 ${name}`);
          setSearchParams({ template: name });
          applied.current = `template:${name}`;
        },
        onError: (error) => setSubmitError(error),
      },
    );
  };

  const loadError = schemaQuery.error ?? backbones.error ?? datasets.error ?? template.error;
  const ready = isSchema(baseSchema) && backbones.data && datasets.data;

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Title level={3}>新建运行</Typography.Title>
      <ErrorAlert error={loadError} />
      <Card size="small" title="模板">
        <Space wrap>
          <Select
            style={{ minWidth: 220 }}
            placeholder="选择模板加载"
            value={templateName ?? undefined}
            loading={templates.isLoading}
            options={(templates.data ?? []).map((item) => ({ value: item.name, label: item.name }))}
            onChange={(value: string) => {
              applied.current = null;
              setSearchParams({ template: value });
            }}
          />
          <Input
            style={{ width: 200 }}
            placeholder="新模板名"
            value={newTemplateName}
            onChange={(event) => setNewTemplateName(event.target.value)}
          />
          <Button onClick={handleSaveTemplate} loading={saveTemplate.isPending}>
            另存为模板
          </Button>
        </Space>
      </Card>
      <ErrorAlert error={submitError} />
      <Card loading={!ready && !loadError}>
        {ready && (
          <RunConfigForm
            baseSchema={baseSchema}
            optionSchemas={optionSchemas}
            backbones={backbones.data}
            datasetIds={datasets.data.map((item) => item.id)}
            formData={formData}
            extraErrors={extraErrors}
            submitText="预览并提交"
            onChange={(value) => {
              setFormData(value);
              setExtraErrors(undefined);
            }}
            onSubmit={handleSubmit}
          />
        )}
      </Card>
      <Modal
        title="提交前预览"
        open={preview !== null}
        okText="提交"
        cancelText="返回修改"
        confirmLoading={submit.isPending}
        onOk={confirmSubmit}
        onCancel={() => setPreview(null)}
        width={720}
      >
        <pre style={{ maxHeight: "60vh", overflow: "auto", margin: 0 }}>
          {JSON.stringify(preview, null, 2)}
        </pre>
      </Modal>
    </Space>
  );
}
