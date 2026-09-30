# Forms and Charts

> Schema-driven forms, ECharts components, and time display.

---

## Run Config Form

- The base schema comes from `GET /api/schema/run-config`: `run_config` (RunConfig JSON Schema) and `backbone_options` (backbone name → Options schema).
- Capabilities, license, and install state come from `GET /api/backbones`.
- Change the schema only with pure functions in `components/forms/schemaTransforms.ts`:
  - `withBackboneOptions(schema, optionsSchema)` replaces `backbone.options` with the selected backbone's Options schema.
  - `withAllowedModes(schema, capabilities, taskType)` keeps only allowed `mode` values. A `classify` task allows only `head`.
  - `withChoices(schema, path, values)` sets the `enum` of the dataset id and the backbone name from the API lists.
  - `toExtraErrors(detail, formData)` maps a 422 `detail` to `extraErrors`.
- Render with `@rjsf/antd` `Form` and `@rjsf/validator-ajv8`. `liveValidate` is off. Validate on submit.
- A backbone with `installed: false` shows as disabled with the missing requirement (`ui:enumDisabled`, `ui:enumNames`).
- Create the form with `generateForm<FormValue>()` from `@rjsf/antd`. The default `Form` export is not generic.
- Give the `Form` a `key` from the backbone name and the task type. rjsf 6.10 does not apply a new schema that the parent sets during a user change (`isProcessingUserChange`), so the Options fields stay stale. The `key` remounts the form when the schema changes.
- When the backbone changes, reset `backbone.options` and set `mode` to an allowed value in `onChange`.
- Do not write a form field for one backbone or one task by hand. If the schema is not enough, add `title`, `description`, or `json_schema_extra` in the Pydantic model.

---

## Charts

Use ECharts with modular imports to keep the bundle small:

```ts
// src/components/charts/EChart.tsx
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

- `EChart.tsx` wraps `ReactEChartsCore` from `echarts-for-react/esm/core`. Do not import `echarts-for-react/lib/core`: in the Vite production build its default export is a module object, and React fails with error #130.
- Tests mock `echarts-for-react/esm/core` in `tests/setup.ts`, because jsdom has no canvas.
- echarts-for-react creates the chart only after the first ECharts `finished` event, which needs `requestAnimationFrame`. A hidden browser tab or pane does not run `requestAnimationFrame` or `ResizeObserver`, so no canvas appears there. Check chart options in that case by rendering them with the ECharts SVG server-side renderer.

| Component         | Content                                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| `ForecastChart`   | Context, truth, prediction mean, band between the quantile levels nearest 0.1 and 0.9 (a stacked lower line and a width line with `areaStyle`), vertical line at the origin |
| `SeriesChart`     | Bucket means from the series API. A `dataZoom` change requests the new range after 500 ms without change. |
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
- Format all times in `utils/format.ts` (`formatDataTime`, `formatSystemTime`). Do not format times inline in components.
- `shiftDataTime(value, freq, steps)` adds grid steps to a data time with UTC arithmetic on the wall-clock value, so no daylight-saving shift occurs. Use it for the context start of a forecast chart and for prediction target times.

---

## Comparison Warnings

The compare API returns `warnings` for different datasets, tasks, context lengths, horizons, origin sets, unsuccessful runs, and ingestion jobs. The additive contract is in [Comparison Warning Contract](../backend/error-handling.md#comparison-warning-contract).

- Show every warning above the table with antd `Alert type="warning"`. Preserve service order, including repeated codes and identical entries. A React key must distinguish each entry.
- Use the warning code for the Chinese main message. Use optional `run_id` and `split` for context; preserve their original values. Resolve the run name and state by exact ID in `columns`, and use `StateTag` for the state. Do not parse English messages.
- Keep a Chinese generic message and the original message for older responses, absent/null context, or missing run columns. Unknown codes retain both the original code and message. Render all content as text.
- Keep the run selection controls restricted to experiments. Send IDs from a manual comparison URL to the API and show the returned ingestion warning without discarding the selected ingestion column.
- Preserve `null` as `—`, metric and chart behavior, and table-local horizontal scrolling. Long warning IDs and messages must wrap at 390 px without clipping or page-level horizontal overflow.
- Page tests mock fetch with English service messages and cover all seven codes, context fallbacks, repeated codes, and manual mixed URLs. Visible browser checks use isolated synthetic terminal jobs at 390 px and 1280 px.
