// Independently test cumulative resource windows without opening a browser.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const sourceCode = fs.readFileSync(new URL('../measurement/measure.mjs', import.meta.url), 'utf8');
const functions = sourceCode.slice(sourceCode.indexOf('const ORIGIN ='), sourceCode.indexOf('async function attachNetwork'));
const { accounting } = vm.runInNewContext(functions + '\n({ accounting });', { URL });
const resource = (name, startTime, responseEnd, body, transfer) => ({
  name: 'http://127.0.0.1:9000/' + name, startTime, responseEnd,
  encodedBodySize: body, decodedBodySize: body, transferSize: transfer,
});
const document = resource('runs', 0, 10, 10, 600);
const firstAsset = resource('assets/entry.js', 5, 80, 100, 400);
const crossing = resource('api/crossing', 90, 120, 250, 550);
const betweenStages = resource('assets/late.js', 150, 160, 200, 500);
const targetAsset = resource('assets/target.js', 210, 260, 50, 350);
const cachedAgain = resource('assets/entry.js', 220, 270, 100, 0);
const source = { start: 0, end: 100, navigation: [document], resources: [firstAsset] };
const target = {
  start: 200, end: 300, navigation: [document],
  resources: [firstAsset, crossing, betweenStages, targetAsset, cachedAgain],
};
const result = accounting(source, target);
assert.equal(result.entry.uniqueUrlCount, 2);
assert.equal(result.navigationWindow.requestEntryCount, 2);
assert.equal(result.navigationIncrement.uniqueUrlCount, 1);
assert.equal(result.navigationIncrement.encodedBodyBytesUrlUnion, 50);
assert.equal(result.cumulative.uniqueUrlCount, 5);
assert.equal(result.cumulative.encodedBodyBytesUrlUnion, 610);
assert.equal(result.cumulative.transferBytesSum, 2400);
assert.equal(result.cumulative.requestEntryCount, 6);
console.log(JSON.stringify({
  passed: true, assertions: 8,
  coverage: ['cross-entry-boundary response', 'between-stage request', 'cached repeated URL', 'new target URL'],
  expectedCumulative: { uniqueUrlCount: 5, bodyBytes: 610, transferBytes: 2400, requestCount: 6 },
}));
