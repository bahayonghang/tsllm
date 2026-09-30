import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { collectPaint } from '../../browser_probe.mjs';
import { awaitReady } from '../../measure.mjs';

const plain = (value) => JSON.parse(JSON.stringify(value));
const nativePaint = (name, startTime) => ({
  toJSON: () => ({ name, entryType: 'paint', startTime, duration: 0 }),
});

function environment({ supported = true, native = [], observeError = null } = {}) {
  const stage = {
    id: 'entry', kind: 'runs', start: 0, end: 100, duration: 100,
    timeOrigin: 1000, paint: [],
    resources: [{ name: 'http://127.0.0.1:9000/assets/example.js', startTime: 10, responseEnd: 70, transferSize: 125 }],
    navigation: [{ name: 'http://127.0.0.1:9000/runs', startTime: 0, responseEnd: 5 }],
    longTasks: [{ startTime: 20, duration: 60 }],
    observerCostCumulative: { calls: 2, totalMilliseconds: 1 },
  };
  const original = plain(stage);
  const state = { now: 110, native, queued: [], observers: [], timers: new Map(), nextTimer: 1 };
  class Observer {
    static supportedEntryTypes = supported ? ['paint'] : [];
    constructor(callback) { this.callback = callback; this.active = false; state.observers.push(this); }
    observe(options) {
      if (observeError) throw new Error(observeError);
      this.options = plain(options);
      this.active = true;
    }
    takeRecords() { const pending = state.queued; state.queued = []; return pending; }
    disconnect() { this.active = false; }
  }
  const sandbox = {
    window: { __tsllmAssessment: { results: { entry: stage } } },
    performance: {
      now: () => state.now,
      getEntriesByType: (type) => { assert.equal(type, 'paint'); return state.native; },
    },
    PerformanceObserver: Observer,
    setTimeout: (callback, delay) => { const id = state.nextTimer++; state.timers.set(id, { callback, delay }); return id; },
    clearTimeout: (id) => state.timers.delete(id),
  };
  const invoke = (fn, args) => vm.runInNewContext('(' + fn.toString() + ')', sandbox)(args);
  const collect = () => invoke(collectPaint, { id: 'entry', timeoutMs: 1000 });
  const publish = (entries, now = 140) => {
    state.now = now;
    state.native.push(...entries);
    for (const observer of state.observers) if (observer.active) observer.callback({ getEntries: () => entries });
  };
  const timeout = () => {
    for (const timer of [...state.timers.values()]) {
      assert.equal(timer.delay, 1000);
      state.now += timer.delay;
      timer.callback();
    }
  };
  return { stage, original, state, collect, publish, timeout, invoke };
}

function assertReadyUnchanged(result, fixture) {
  const { paint, paintAtReady, paintCollection, ...ready } = plain(result);
  const { paint: originalPaint, ...originalReady } = fixture.original;
  assert.deepEqual(ready, originalReady);
  assert.deepEqual(paintAtReady, originalPaint);
  assert.deepEqual(fixture.stage, fixture.original);
  assert.equal(paintCollection.readyEndpoint, fixture.original.end);
}

test('late publication retains a native FCP before the frozen endpoint', async () => {
  const fixture = environment();
  let settled = false;
  const promise = fixture.collect().then((value) => { settled = true; return value; });
  await Promise.resolve();
  assert.equal(settled, false);
  assert.deepEqual(fixture.state.observers[0].options, { type: 'paint', buffered: true });
  fixture.publish([nativePaint('first-paint', 80), nativePaint('first-contentful-paint', 90)], 140);
  const result = await promise;
  assertReadyUnchanged(result, fixture);
  assert.equal(result.paint.find((entry) => entry.name === 'first-contentful-paint').startTime, 90);
  assert.equal(result.paintCollection.status, 'observed');
  assert.equal(result.paintCollection.startedAt, 110);
  assert.equal(result.paintCollection.collectedAt, 140);
  assert.equal(result.paintCollection.waitMs, 30);
  assert.equal(fixture.state.timers.size, 0);
  assert.equal(fixture.state.observers[0].active, false);
});

test('already published native paint completes without an observer or wait', async () => {
  const fixture = environment({ native: [nativePaint('first-contentful-paint', 90)] });
  const result = await fixture.collect();
  assertReadyUnchanged(result, fixture);
  assert.equal(result.paintCollection.status, 'observed');
  assert.equal(result.paintCollection.waitMs, 0);
  assert.equal(fixture.state.observers.length, 0);
});

test('a native FCP after ready remains after ready without moving the endpoint', async () => {
  const fixture = environment();
  const promise = fixture.collect();
  fixture.publish([nativePaint('first-contentful-paint', 125)], 140);
  const result = await promise;
  assertReadyUnchanged(result, fixture);
  assert.equal(result.paint[0].startTime, 125);
  assert.equal(result.end, 100);
  assert.equal(result.paintCollection.scope, 'document');
});

test('a bounded timeout reports missing paint without creating values', async () => {
  const fixture = environment();
  const promise = fixture.collect();
  fixture.timeout();
  const result = await promise;
  assertReadyUnchanged(result, fixture);
  assert.deepEqual(plain(result.paint), []);
  assert.equal(result.paintCollection.status, 'timeout');
  assert.equal(result.paintCollection.waitMs, 1000);
  assert.equal(fixture.state.timers.size, 0);
  assert.equal(fixture.state.observers[0].active, false);
});

test('queued native records are drained before a timeout result', async () => {
  const fixture = environment();
  const promise = fixture.collect();
  fixture.state.queued.push(nativePaint('first-contentful-paint', 90));
  fixture.timeout();
  const result = await promise;
  assertReadyUnchanged(result, fixture);
  assert.equal(result.paintCollection.status, 'observed');
  assert.equal(result.paint[0].startTime, 90);
});

test('unsupported paint and observer failure have explicit separate status', async () => {
  const unsupported = environment({ supported: false });
  const first = await unsupported.collect();
  assertReadyUnchanged(first, unsupported);
  assert.equal(first.paintCollection.status, 'unsupported');
  assert.deepEqual(plain(first.paint), []);
  assert.equal(unsupported.state.timers.size, 0);
  const broken = environment({ observeError: 'Synthetic observer failure' });
  const second = await broken.collect();
  assertReadyUnchanged(second, broken);
  assert.equal(second.paintCollection.status, 'error');
  assert.match(second.paintCollection.error, /Synthetic observer failure/);
  assert.equal(broken.state.timers.size, 0);
});

test('awaitReady waits for native collection before the caller can navigate', async () => {
  const fixture = environment();
  const page = {
    waitForFunction: async (_predicate, id) => assert.equal(id, 'entry'),
    evaluate: (fn, argument) => fixture.invoke(fn, argument),
  };
  let nextAction = false;
  const promise = awaitReady(page, 'entry').then((result) => { nextAction = true; return result; });
  await new Promise(setImmediate);
  assert.equal(nextAction, false);
  fixture.publish([nativePaint('first-contentful-paint', 90)]);
  const result = await promise;
  assert.equal(nextAction, true);
  assertReadyUnchanged(result, fixture);
  assert.equal(result.paintCollection.status, 'observed');
});

test('the original readiness probe is unchanged by the supplemental collector', () => {
  const before = fs.readFileSync(new URL('./before/browser_probe.mjs', import.meta.url), 'utf8').replaceAll('\r\n', '\n').trimEnd();
  const after = fs.readFileSync(new URL('../../browser_probe.mjs', import.meta.url), 'utf8').replaceAll('\r\n', '\n');
  assert.ok(after.startsWith(before + '\n'));
});
