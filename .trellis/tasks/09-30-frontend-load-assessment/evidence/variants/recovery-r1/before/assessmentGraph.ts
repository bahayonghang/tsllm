import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Plugin } from "vite";

function moduleName(id: string): string {
  const normalized = id.replaceAll("\\", "/");
  const dependency = normalized.lastIndexOf("/node_modules/");
  if (dependency >= 0) return `node_modules/${normalized.slice(dependency + 14)}`;
  const source = normalized.lastIndexOf("/web/");
  return source >= 0 ? `web/${normalized.slice(source + 5)}` : normalized;
}

export function assessmentGraph(): Plugin {
  return {
    name: "assessment-output-graph",
    apply: "build",
    generateBundle(_options, bundle) {
      const chunks = Object.values(bundle).flatMap((output) =>
        output.type === "chunk"
          ? [
              {
                file: output.fileName,
                entry: output.isEntry,
                dynamicEntry: output.isDynamicEntry,
                facade: output.facadeModuleId ? moduleName(output.facadeModuleId) : null,
                imports: output.imports,
                dynamicImports: output.dynamicImports,
                modules: Object.entries(output.modules).map(([id, metadata]) => ({
                  id: moduleName(id),
                  renderedLength: metadata.renderedLength,
                })),
              },
            ]
          : [],
      );
      const directory = resolve(process.cwd(), "../assessment");
      mkdirSync(directory, { recursive: true });
      writeFileSync(
        resolve(directory, "graph.json"),
        `${JSON.stringify({ chunks }, null, 2)}\n`,
        "utf8",
      );
    },
  };
}
