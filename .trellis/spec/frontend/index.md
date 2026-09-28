# Frontend Development Guidelines

> Conventions for the React UI in `web/`.

---

## Status

The team decided these conventions on 2026-09-28, before `web/` exists. The source is `.trellis/tasks/09-28-web-ui/` (`prd.md`, `design.md`). Package versions were checked on the npm registry on 2026-09-28. When the web-ui child lands, replace the reference examples with real file paths and set Status to `Verified`.

---

## Guidelines Index

| Guide                                           | Description                                                 | Status  |
| ----------------------------------------------- | ----------------------------------------------------------- | ------- |
| [Directory Structure](./directory-structure.md) | `web/` layout, routes, naming                               | Decided |
| [API Client](./api-client.md)                   | Generated types, fetch client, errors, TanStack Query, SSE  | Decided |
| [Forms and Charts](./forms-and-charts.md)       | Schema-driven forms, ECharts components, time display       | Decided |
| [Quality Guidelines](./quality-guidelines.md)   | pnpm scripts, Biome, TypeScript, Vitest, forbidden patterns | Decided |

---

## Stack

| Area            | Package (major version)                                                           |
| --------------- | --------------------------------------------------------------------------------- |
| Build           | Vite 8, pnpm 12, Node 26                                                          |
| UI              | React 19, antd 6, @ant-design/icons 6                                             |
| Language        | TypeScript 5.9 (strict). Not 7.x: openapi-typescript 7.13 needs `typescript ^5.x` |
| Forms           | @rjsf/core, @rjsf/antd, @rjsf/validator-ajv8 6.x                                  |
| Charts          | echarts 6, echarts-for-react 3                                                    |
| Data            | @tanstack/react-query 5, openapi-fetch, openapi-typescript 7                      |
| Routing         | react-router 8                                                                    |
| Lint and format | Biome 2                                                                           |
| Tests           | Vitest 5, @testing-library/react 16, jsdom                                        |

---

## Core Rules

1. The backend is the source of truth for types and forms. Generate API types from `web/openapi.json`. Render run forms from the JSON Schema.
2. The UI does not contain a backbone name, dataset id, or channel name in code.
3. The UI text is Chinese. Code identifiers and comments are English.
4. The UI reads data only through `/api`. It never reads `runs/`, `cache/`, or `data/`.
