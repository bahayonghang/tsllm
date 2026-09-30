import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { run } from './measure.mjs';

const task = fileURLToPath(new URL('../', import.meta.url));
const sandbox = path.join(task, 'isolation', 'guard-tests');
fs.mkdirSync(sandbox, { recursive: true });
const hash = (data) => createHash('sha256').update(data).digest('hex');
function fixture() {
  const root = fs.mkdtempSync(path.join(sandbox, 'run-'));
  const fixtures = path.join(root, 'fixtures');
  const product = path.join(root, 'product');
  fs.mkdirSync(fixtures);
  fs.mkdirSync(path.join(product, 'web/dist'), { recursive: true });
  fs.writeFileSync(path.join(fixtures, 'manifest.json'), JSON.stringify({ files: {} }));
  fs.writeFileSync(path.join(product, 'web/dist/index.html'), 'synthetic');
  fs.writeFileSync(path.join(product, 'source.txt'), 'source');
  const experiment = { fixture_root: fixtures,
    measurement_identity: { scripts: {}, fixture_manifest_sha256: hash(fs.readFileSync(path.join(fixtures, 'manifest.json'))) },
    variants: { B1: { root: product, source: { files: { 'source.txt': { sha256: hash('source') } } },
      build: { files: { 'index.html': { sha256: hash('synthetic'), bytes: 9 } } } } },
  };
  const file = path.join(root, 'experiment.json');
  fs.writeFileSync(file, JSON.stringify(experiment));
  return { root, fixtures, product, experiment, args: { experiment: file, 'fixture-root': fixtures, variant: 'B1', output: path.join(root, 'raw') } };
}

test('nonempty output without a sidecar is rejected before browser launch', async () => {
  const context = fixture();
  fs.mkdirSync(context.args.output);
  fs.writeFileSync(path.join(context.args.output, 'retained.json'), 'first-attempt');
  await assert.rejects(run(context.args), /Nonempty output has no version sidecar/);
  assert.equal(fs.readFileSync(path.join(context.args.output, 'retained.json'), 'utf8'), 'first-attempt');
  assert.equal(fs.existsSync(context.args.output + '-instrumentation.json'), false);
});

test('a sidecar from a different revision is rejected without overwrite', async () => {
  const context = fixture();
  const sidecar = context.args.output + '-instrumentation.json';
  fs.writeFileSync(sidecar, 'previous-revision');
  await assert.rejects(run(context.args), /Different measurement instrument revision/);
  assert.equal(fs.readFileSync(sidecar, 'utf8'), 'previous-revision');
});

test('changed production bytes are rejected before output creation', async () => {
  const context = fixture();
  fs.writeFileSync(path.join(context.product, 'web/dist/index.html'), 'changed');
  await assert.rejects(run(context.args), /Built file changed/);
  assert.equal(fs.existsSync(context.args.output), false);
});

test('changed frozen source is rejected before output creation', async () => {
  const context = fixture();
  fs.writeFileSync(path.join(context.product, 'source.txt'), 'changed');
  await assert.rejects(run(context.args), /Source file changed/);
  assert.equal(fs.existsSync(context.args.output), false);
});
