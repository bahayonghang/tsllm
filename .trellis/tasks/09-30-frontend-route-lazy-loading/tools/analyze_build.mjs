// Inspect original Vite output without a build plugin or source instrumentation.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((items, value, index, values) => {
  if (index % 2 === 0) items.push([value.slice(2), values[index + 1]]);
  return items;
}, []));
for (const name of ['snapshot', 'output']) if (!args[name]) throw new Error('Missing --' + name);
const source = JSON.parse(fs.readFileSync(args.snapshot, 'utf8'));
const root = path.resolve(source.root);
const dist = path.join(root, 'web/dist');
const require = createRequire(pathToFileURL(path.join(root, 'web/package.json')));
const ts = require('typescript');
const hash = (value) => createHash('sha256').update(value).digest('hex');
const walk = (directory) => fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => entry.isDirectory() ? walk(path.join(directory, entry.name)) : [path.join(directory, entry.name)]);
const files = {};
const graph = {};
const paths = walk(dist).sort();
const compression = JSON.parse(execFileSync(args.python ?? 'python', ['-c', 'import gzip,json,platform,sys,zlib; from pathlib import Path; paths=json.load(sys.stdin); print(json.dumps({"python":platform.python_version(),"zlib":zlib.ZLIB_RUNTIME_VERSION,"bytes":{p:len(gzip.compress(Path(p).read_bytes(),compresslevel=9,mtime=0)) for p in paths}}))'], { input: JSON.stringify(paths), encoding: 'utf8' }));
for (const file of paths) {
  const data = fs.readFileSync(file);
  const name = path.relative(dist, file).split(path.sep).join('/');
  files[name] = { sha256: hash(data), bytes: data.length, mtime_ns: String(fs.statSync(file, { bigint: true }).mtimeNs), gzip_bytes: compression.bytes[file] };
  if (!file.endsWith('.js')) continue;
  const parsed = ts.createSourceFile(file, data.toString('utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  const imported = { static: [], dynamic: [] };
  const add = (kind, specifier) => {
    if (ts.isStringLiteral(specifier)) imported[kind].push(path.posix.normalize(path.posix.join(path.posix.dirname(name), specifier.text)));
  };
  const visit = (node) => {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier) add('static', node.moduleSpecifier);
    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword && node.arguments[0]) add('dynamic', node.arguments[0]);
    ts.forEachChild(node, visit);
  };
  visit(parsed);
  graph[name] = Object.fromEntries(Object.entries(imported).map(([key, values]) => [key, [...new Set(values)].sort()]));
}
const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const entryAssets = [...html.matchAll(/(?:src|href)=["']([^"']+)["']/g)].map((item) => item[1]).filter((url) => url.startsWith('/assets/')).map((url) => url.slice(1));
const staticClosure = new Set();
const visitStatic = (name) => {
  if (staticClosure.has(name)) return;
  staticClosure.add(name);
  for (const dependency of graph[name]?.static ?? []) visitStatic(dependency);
};
entryAssets.forEach(visitStatic);
const canonical = Object.fromEntries(Object.entries(files).map(([name, item]) => [name, { bytes: item.bytes, sha256: item.sha256 }]));
const result = {
  schema_version: 1, variant: source.variant, root, baseline: source.baseline, source_version: source.source_version,
  source_snapshot: path.resolve(args.snapshot), dist_version: hash(JSON.stringify(canonical)), files,
  entry_assets: entryAssets, initial_static_closure: [...staticClosure].sort(), imports: graph,
  route_chunks: Object.keys(files).filter((name) => /(?:Datasets|DatasetDetail|Runs|RunNew|RunDetail|Compare|System)Page-/.test(name)),
  totals: { bytes: Object.values(files).reduce((sum, item) => sum + item.bytes, 0), gzip_bytes: Object.values(files).reduce((sum, item) => sum + item.gzip_bytes, 0) },
  gzip_method: { function: 'gzip.compress', compresslevel: 9, mtime: 0, python: compression.python, zlib: compression.zlib, meaning: 'Offline estimate per file; HTTP transfer is measured separately' },
  graph_method: 'TypeScript parser on emitted JavaScript import/export declarations and import() calls; no Vite plugin',
  analyzer_sha256: hash(fs.readFileSync(new URL(import.meta.url))),
};
fs.mkdirSync(path.dirname(args.output), { recursive: true });
fs.writeFileSync(args.output, JSON.stringify(result, null, 2) + '\n', { encoding: 'utf8', flag: 'wx' });
console.log(JSON.stringify({ variant: result.variant, source_version: result.source_version, dist_version: result.dist_version, files: Object.keys(files).length, totals: result.totals, route_chunks: result.route_chunks }));
