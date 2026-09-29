# Frontend Development Guidelines

> Conventions for the React UI in `web/`.

---

## Status

Status: **Verified** on 2026-09-29 by the web-ui child (`.trellis/tasks/09-28-web-ui/`). `check`, `test`, `build`, and `gen:api` pass. The in-app browser acceptance (web-ui AC4–AC6) passed against the running service. The examples in these guides name real files in `web/`.

---

## Guidelines Index

| Guide                                           | Description                                                 | Status  |
| ----------------------------------------------- | ----------------------------------------------------------- | ------- |
| [Directory Structure](./directory-structure.md) | `web/` layout, routes, naming                               | Verified |
| [API Client](./api-client.md)                   | Generated types, fetch client, errors, TanStack Query, SSE  | Verified |
| [Forms and Charts](./forms-and-charts.md)       | Schema-driven forms, ECharts components, time display       | Verified |
| [Quality Guidelines](./quality-guidelines.md)   | pnpm scripts, Biome, TypeScript, Vitest, forbidden patterns | Verified |

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
