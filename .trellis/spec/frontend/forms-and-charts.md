# Forms and Charts

> Schema-driven forms, ECharts components, and time display.

---

## Run Config Form

- The base schema comes from `GET /api/schema/run-config`: `run_config` (RunConfig JSON Schema) and `backbone_options` (backbone name → Options schema).
- Capabilities, license, and install state come from `GET /api/backbones`.
- Change the schema only with pure functions in `components/forms/schemaTransforms.ts`:
  - `withBackboneOptions(schema, optionsSchema)` replaces `backbone.options` with the selected backbone's Options schema.
  - `withAllowedModes(schema, capabilities, taskType)` keeps only allowed `mode` values. A `classify` task allows only `head`.
- Render with `@rjsf/antd` `Form` and `@rjsf/validator-ajv8`. `liveValidate` is off. Validate on submit.
- A backbone with `installed: false` shows as disabled with the missing requirement.
- Do not write a form field for one backbone or one task by hand. If the schema is not enough, add `title`, `description`, or `json_schema_extra` in the Pydantic model.

---

## Charts

Use ECharts with modular imports to keep the bundle small:

```ts
// reference pattern
import * as echarts from "echarts/core";
import { LineChart, BarChart, CustomChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
  MarkLineComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
echarts.use([
  LineChart,
  BarChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
  MarkLineComponent,
  CanvasRenderer,
]);
```

| Component         | Content                                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| `ForecastChart`   | Context, truth, prediction mean, q0.1–q0.9 band (two lines with `areaStyle`), vertical line at the origin |
| `SeriesChart`     | Bucket means from the series API. A `dataZoom` change requests the new range.                             |
| `SegmentTimeline` | Segments as intervals (`custom` series). Split boundaries `fit`, `val`, `cal`, `test` in 4 colors.        |
| `RocPrChart`      | `curves.roc` and `curves.pr`, one line per split                                                          |
| `ConfusionMatrix` | antd `Table`, not ECharts                                                                                 |
| `CompareBarChart` | One metric, grouped by split, one bar per run                                                             |

- Chart components receive plain arrays through props. They do not call the API.
- Read colors from the antd theme token so that the dark theme is readable.
- Show units from the channel dictionary in axis names. Show `null` metrics as `—`, not `0`.

---

## Time Display

- Data times (series, origins, segments, split boundaries) are ISO strings without an offset. Show them unchanged. Do not convert them to a time zone.
- System times (`created_at`, `finished_at`, event `ts`) are UTC with an offset. Show them in the browser time zone.
- Format all times in `utils/format.ts`. Do not format times inline in components.

---

## Comparison Warnings

The compare API returns `warnings` (different dataset, task, context length, horizon, `origin_set_hash`, or a run that did not succeed). Show every warning above the table with antd `Alert type="warning"`. Do not hide them.
