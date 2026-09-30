// Run against one service that the main session already owns on 127.0.0.1:9000.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { installProbe } from './browser_probe.mjs';

const ORIGIN = 'http://127.0.0.1:9000';
const SCENARIOS = ['cold-runs', 'warm-runs', 'first-form', 'first-compare', 'first-dataset', 'first-forecast'];

function parseArguments(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith('--') || argv[index + 1] === undefined) throw new Error('Use --name value pairs');
    args[argv[index].slice(2)] = argv[index + 1];
  }
  for (const name of ['playwright-root', 'browser-executable', 'fixture-root', 'output', 'variant', 'sample']) if (!args[name]) throw new Error('Missing --' + name);
  if (!['B0', 'B1', 'B2'].includes(args.variant)) throw new Error('Variant must be B0, B1, or B2');
  args.sample = Number(args.sample);
  if (!Number.isInteger(args.sample) || args.sample < 1) throw new Error('Sample must be a positive integer');
  args.attempt = Number(args.attempt ?? 1);
  args.scenarios = args.scenarios ? args.scenarios.split(',') : SCENARIOS;
  if (!args.scenarios.every((value) => [...SCENARIOS, 'journey'].includes(value))) throw new Error('Unknown scenario');
  return args;
}

function entries(stage) {
  return [...stage.navigation.map((item) => ({ ...item, initiatorType: 'document' })), ...stage.resources];
}

function describeResources(resourceEntries) {
  const urls = new Map();
  for (const item of resourceEntries) {
    if (!item.name.startsWith(ORIGIN + '/')) continue;
    const old = urls.get(item.name);
    if (!old || item.encodedBodySize > old.encodedBodySize) urls.set(item.name, {
      url: item.name, encodedBodySize: item.encodedBodySize, decodedBodySize: item.decodedBodySize,
      category: new URL(item.name).pathname.startsWith('/assets/') ? 'build-asset' : new URL(item.name).pathname.startsWith('/api/') ? 'api' : 'document-or-other',
    });
  }
  return {
    uniqueUrlCount: urls.size, requestEntryCount: resourceEntries.length,
    transferBytesSum: resourceEntries.reduce((sum, item) => sum + item.transferSize, 0),
    encodedBodyBytesUrlUnion: [...urls.values()].reduce((sum, item) => sum + item.encodedBodySize, 0),
    decodedBodyBytesUrlUnion: [...urls.values()].reduce((sum, item) => sum + item.decodedBodySize, 0),
    urls: [...urls.values()],
    // Repeated API URLs can return different bodies. The unique-URL body metric
    // uses the largest observed body; transferBytesSum retains every request.
    bodyUnionRule: 'Largest observed body per full URL; actual transfer sums retain repeated requests',
  };
}

function accounting(source, target) {
  const sourceEntries = entries(source);
  const sourceUrls = new Set(sourceEntries.map((item) => item.name));
  if (!target) return { entry: describeResources(sourceEntries), navigationWindow: null, navigationIncrement: null, cumulative: describeResources(sourceEntries) };
  const targetEntries = entries(target).filter((item) => item.startTime >= target.start && item.responseEnd <= target.end);
  const increment = targetEntries.filter((item) => !sourceUrls.has(item.name));
  return { entry: describeResources(sourceEntries), navigationWindow: describeResources(targetEntries), navigationIncrement: describeResources(increment), cumulative: describeResources(entries(target)) };
}

async function attachNetwork(context, page) {
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: false });
  const requests = new Map();
  const ensure = (id) => { if (!requests.has(id)) requests.set(id, { requestId: id }); return requests.get(id); };
  cdp.on('Network.requestWillBeSent', (event) => Object.assign(ensure(event.requestId), { url: event.request.url, method: event.request.method, requestHeaders: event.request.headers, resourceType: event.type, timestamp: event.timestamp, wallTime: event.wallTime, initiatorType: event.initiator.type }));
  cdp.on('Network.requestServedFromCache', (event) => Object.assign(ensure(event.requestId), { requestServedFromCache: true }));
  cdp.on('Network.responseReceived', (event) => Object.assign(ensure(event.requestId), { status: event.response.status, responseHeaders: event.response.headers, mimeType: event.response.mimeType, protocol: event.response.protocol, fromDiskCache: event.response.fromDiskCache ?? false, fromServiceWorker: event.response.fromServiceWorker ?? false, fromPrefetchCache: event.response.fromPrefetchCache ?? false, responseTiming: event.response.timing ?? null }));
  cdp.on('Network.responseReceivedExtraInfo', (event) => Object.assign(ensure(event.requestId), { networkStatusCode: event.statusCode, networkResponseHeaders: event.headers }));
  cdp.on('Network.loadingFinished', (event) => Object.assign(ensure(event.requestId), { encodedDataLength: event.encodedDataLength, completedTimestamp: event.timestamp }));
  cdp.on('Network.loadingFailed', (event) => Object.assign(ensure(event.requestId), { failed: true, errorText: event.errorText, canceled: event.canceled ?? false }));
  return { cdp, requests };
}

async function awaitReady(page, id) {
  await page.waitForFunction((name) => !!window.__tsllmAssessment?.results[name], id, { timeout: 45000, polling: 'raf' });
  return page.evaluate((name) => window.__tsllmAssessment.results[name], id);
}

async function clickStage(page, id, kind, locator) {
  await page.evaluate(({ id, kind }) => window.__tsllmAssessment.arm(id, kind, 'trusted-ui-click'), { id, kind });
  await locator.click();
  return awaitReady(page, id);
}

async function programmaticStage(page, id, kind, route) {
  await page.evaluate(({ id, kind, route }) => window.__tsllmAssessment.navigate(id, kind, route), { id, kind, route });
  return awaitReady(page, id);
}

async function checkPreview(page) {
  await page.getByRole('combobox').filter({ visible: true }).first().click();
  await page.getByText('synthetic-preview', { exact: true }).last().click();
  await page.locator('#root_name').waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.querySelector('#root_name')?.value === 'Synthetic forecast' && document.querySelector('#root_task_context_length')?.value === '12' && document.querySelector('#root_task_horizon')?.value === '6');
  const preview = await clickStage(page, 'preview', 'preview', page.getByRole('button', { name: '预览并提交', exact: true }));
  await page.getByRole('button', { name: '返回修改', exact: true }).click();
  return preview;
}

function classifyCache(request) {
  if (request.fromServiceWorker) return 'service-worker';
  if (request.networkStatusCode === 304) return 'http-304-revalidation';
  if (request.fromDiskCache) return 'disk-cache';
  if (request.fromPrefetchCache) return 'prefetch-cache';
  if (request.requestServedFromCache) return 'cache-reported-no-disk-flag';
  return 'network-or-unreported';
}

async function sample(browser, configuration, args, scenario) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, locale: 'zh-CN', timezoneId: 'America/Chicago', serviceWorkers: 'block' });
  const page = await context.newPage();
  const network = await attachNetwork(context, page);
  await network.cdp.send('Network.clearBrowserCache');
  const initialKind = scenario === 'first-dataset' ? 'datasets' : 'runs';
  await page.addInitScript(installProbe, { ...configuration, initialKind });
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (error) => pageErrors.push(String(error)));
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  const record = { schema_version: 1, variant: args.variant, sample: args.sample, attempt: args.attempt, scenario, valid: false, browser: browser.version(), browserProfile: 'Installed Edge, Playwright headless, no network/CPU throttling, loopback', viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, cacheMode: scenario === 'warm-runs' ? 'Warm: reload same page/context after verified cold /runs' : 'Cold browser HTTP cache: fresh context + Network.clearBrowserCache; OS/process/code cache not claimed cold', sourceRoute: initialKind === 'datasets' ? '/datasets' : '/runs', startedAt: new Date().toISOString(), stages: [] };
  try {
    await page.goto(ORIGIN + record.sourceRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const source = await awaitReady(page, 'entry');
    record.stages.push(source);
    const coldAssets = [...network.requests.values()].filter((item) => item.url?.includes('/assets/'));
    if (!coldAssets.length || coldAssets.some((item) => item.fromDiskCache || item.fromServiceWorker || item.requestServedFromCache || item.networkStatusCode === 304)) throw new Error('Cold source assets were absent or reported a cache hit');
    if (scenario === 'cold-runs') record.accounting = accounting(source);
    else if (scenario === 'warm-runs') {
      const warmStartWallTime = Date.now();
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
      const target = await awaitReady(page, 'entry');
      target.id = 'warm';
      record.stages.push(target);
      record.warmStartWallTime = warmStartWallTime;
      record.accounting = { coldPrime: describeResources(entries(source)), warm: describeResources(entries(target)) };
    } else if (scenario === 'first-form') {
      const target = await clickStage(page, 'target', 'form', page.getByRole('button', { name: '新建运行', exact: true }));
      record.stages.push(target);
      record.accounting = accounting(source, target);
      record.preview = await checkPreview(page);
      record.accountingWithPreview = describeResources(entries(record.preview));
    } else if (scenario === 'first-compare') {
      const route = '/compare?run_ids=' + Object.values(configuration.ids).join(',');
      const target = await programmaticStage(page, 'target', 'compare', route);
      record.stages.push(target);
      record.accounting = accounting(source, target);
    } else if (scenario === 'first-dataset') {
      const target = await clickStage(page, 'target', 'dataset', page.getByRole('link', { name: 'synthetic-alpha', exact: true }));
      record.stages.push(target);
      record.accounting = accounting(source, target);
    } else if (scenario === 'first-forecast') {
      const target = await clickStage(page, 'target', 'forecast', page.getByRole('link', { name: 'Synthetic forecast', exact: true }));
      record.stages.push(target);
      record.accounting = accounting(source, target);
    } else if (scenario === 'journey') {
      const steps = [
        ['form', () => page.getByRole('menuitem').getByRole('link', { name: '新建运行', exact: true }), 'form'],
        ['compare', null, 'compare'],
        ['datasets', () => page.getByRole('menuitem').getByRole('link', { name: '数据集', exact: true }), 'datasets'],
        ['dataset', () => page.getByRole('link', { name: 'synthetic-alpha', exact: true }), 'dataset'],
        ['runs-return', () => page.getByRole('menuitem').getByRole('link', { name: '运行', exact: true }), 'runs'],
        ['forecast', () => page.getByRole('link', { name: 'Synthetic forecast', exact: true }), 'forecast'],
        ['runs-again', () => page.getByRole('menuitem').getByRole('link', { name: '运行', exact: true }), 'runs'],
        ['classify', () => page.getByRole('link', { name: 'Synthetic classification', exact: true }), 'classify'],
        ['system', () => page.getByRole('menuitem').getByRole('link', { name: '系统', exact: true }), 'system'],
      ];
      for (const [id, getLocator, kind] of steps) {
        const stage = getLocator ? await clickStage(page, id, kind, getLocator()) : await programmaticStage(page, id, kind, '/compare?run_ids=' + Object.values(configuration.ids).join(','));
        record.stages.push(stage);
        if (kind === 'form') record.preview = await checkPreview(page);
      }
      record.accounting = { completeJourney: describeResources(entries(record.stages.at(-1))) };
    }
    const primary = record.stages.at(-1);
    record.targetRoute = primary.route;
    record.primaryReadyMilliseconds = primary.duration;
    record.capabilities = await page.evaluate(() => window.__tsllmAssessment.capabilities);
    if (pageErrors.length) throw new Error('Uncaught browser error: ' + pageErrors.join('; '));
    if ([...network.requests.values()].some((item) => item.method && !['GET', 'HEAD', 'OPTIONS'].includes(item.method))) throw new Error('Unexpected mutating HTTP request');
    const failures = [...network.requests.values()].filter((item) => item.failed && !item.canceled || item.status >= 400 && !item.url.endsWith('/favicon.ico'));
    if (failures.length) throw new Error('Resource failure: ' + JSON.stringify(failures.map((item) => ({ url: item.url, status: item.status, error: item.errorText }))));
    record.valid = true;
  } catch (error) {
    record.error = String(error);
    record.diagnostic = await page.evaluate(() => window.__tsllmAssessment?.diagnostic()).catch(() => null);
  } finally {
    record.pageErrors = pageErrors;
    record.consoleErrors = consoleErrors;
    record.network = [...network.requests.values()].map((item) => ({ ...item, cacheClassification: classifyCache(item) }));
    record.finishedAt = new Date().toISOString();
    await context.close();
  }
  return record;
}

export async function run(args) {
  fs.mkdirSync(args.output, { recursive: true });
  const require = createRequire(pathToFileURL(path.join(path.resolve(args['playwright-root']), 'package.json')));
  const { chromium } = require(path.resolve(args['playwright-root']));
  const configuration = JSON.parse(fs.readFileSync(path.join(args['fixture-root'], 'manifest.json'), 'utf8'));
  const browser = await chromium.launch({ executablePath: args['browser-executable'], headless: true, proxy: { server: 'http://127.0.0.1:9', bypass: '127.0.0.1,localhost' }, args: ['--disable-background-networking', '--disable-component-update', '--no-first-run'] });
  let failed = 0;
  try {
    for (const scenario of args.scenarios) {
      const destination = path.join(args.output, args.variant + '-' + scenario + '-s' + args.sample + '-a' + args.attempt + '.json');
      if (fs.existsSync(destination)) throw new Error('Existing attempt preserved: ' + destination);
      const result = await sample(browser, configuration, args, scenario);
      fs.writeFileSync(destination, JSON.stringify(result, null, 2) + '\n', { encoding: 'utf8', flag: 'wx' });
      console.log(JSON.stringify({ variant: args.variant, sample: args.sample, attempt: args.attempt, scenario, valid: result.valid, primaryReadyMilliseconds: result.primaryReadyMilliseconds, error: result.error }));
      if (!result.valid) failed++;
    }
  } finally { await browser.close(); }
  return failed;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const failures = await run(parseArguments(process.argv.slice(2)));
  if (failures) process.exitCode = 1;
}
