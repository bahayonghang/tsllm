# Quality Guidelines

> Tools, tests, and review standards for `web/`.

---

## Scripts

| Script    | Command                                                  | Use                              |
| --------- | -------------------------------------------------------- | -------------------------------- |
| `dev`     | `vite`                                                   | Dev server with `/api` proxy     |
| `build`   | `tsc --noEmit && vite build`                             | Output to `web/dist`             |
| `check`   | `biome check . && tsc --noEmit`                          | Lint, format check, type check   |
| `format`  | `biome format --write .`                                 | Format                           |
| `test`    | `vitest run`                                             | Unit and component tests (jsdom) |
| `gen:api` | `openapi-typescript openapi.json -o src/api/schema.d.ts` | Regenerate API types             |

Run from the repository root with `pnpm -C web run <script>`. A change is complete only when `check`, `test`, and `build` pass.

- `biome.json` sets `vcs.root` to `".."`, because the `.gitignore` file is in the repository root.
- On Windows, an editor hook can write CRLF line ends. Run `npx biome check --write .` in `web/` before `check`.
- The build writes one chunk of about 2.4 MB (786 KB gzip). `chunkSizeWarningLimit` is 2000, so Vite prints a warning. Code splitting is not done.

---

## TypeScript

- `strict: true`, `noUncheckedIndexedAccess: true`.
- No `any`. Use `unknown` and narrow it. Biome rule `noExplicitAny` is an error.
- No `as` cast on API data. The generated types are the contract.

---

## Tests

- Test pure functions (`schemaTransforms.ts`, `format.ts`) with plain Vitest.
- Test components with Testing Library. Query by role and visible text, not by class name.
- Mock the network at the `fetch` level. Do not mock `api/hooks.ts`.
- Required component tests (web-ui AC3): the form changes Options when the backbone changes; unsupported modes are disabled; the SSE hook resumes from `Last-Event-ID` without repeated events; the compare page shows warnings.
- `tests/helpers.tsx` has `renderRoute(url)` (memory router with the app routes) and `mockFetch(routes)`. `tests/fixtures/run-config.schema.json` is the exported RunConfig schema.
- Tests that use timers (`sse.test.tsx`) use `vi.useFakeTimers()` and advance the timers before they assert.
- Manual acceptance uses the in-app browser at 1280 px and 390 px width. Do not commit screenshots: they contain plant data.
- Check horizontal overflow with `document.documentElement.scrollWidth <= clientWidth` on each page. A same-origin `iframe` with a fixed width checks many pages from one script.
- The header menu uses `disabledOverflow` and wraps. The antd overflow menu needs `ResizeObserver` measurement to collapse. It did not collapse in the hidden pane, and the page overflowed at 390 px.

---

## Forbidden Patterns

| Pattern                                                     | Reason                                          |
| ----------------------------------------------------------- | ----------------------------------------------- |
| Hand-written API types                                      | They drift from the backend                     |
| A backbone name, dataset id, or channel name in a condition | New models and datasets must need no web change |
| `fetch` in a page or chart component                        | All requests go through `api/hooks.ts`          |
| A global state library (Redux, Zustand)                     | URL parameters and the query cache are enough   |
| Full `import * as echarts from "echarts"`                   | Bundle size                                     |
| Time zone conversion of data times                          | Data times have no zone                         |
