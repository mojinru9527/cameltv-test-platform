// B173-26: 统计口径对比 — 工作台 vs 追溯 vs 报告 API 直查
const fs = require('fs');
const { chromium } = require('playwright');
const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';
const EVID = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';

(async () => {
  fs.mkdirSync(EVID, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: STATE, viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  const note = (m) => console.log('###', m);
  await page.goto(BASE + '/workbench', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  const results = {};
  // 工作台 dashboard
  const dash = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/dashboard/overview', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  results.dashboard = dash;
  note('dashboard/overview: ' + JSON.stringify(dash.body ? (dash.body.data || dash.body).slice ? null : JSON.stringify(dash.body).slice(0, 800) : dash.status));

  // 追溯
  const trace = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/trace/overview', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  results.trace = trace;
  note('trace/overview: ' + JSON.stringify(trace.body).slice(0, 800));

  // 统计
  const stats = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/test-cases/stats', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  results.stats = stats;
  note('test-cases/stats: ' + JSON.stringify(stats.body).slice(0, 600));

  // 执行统计
  const execStats = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/dashboard/execution-stats', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  results.execStats = execStats;
  note('execution-stats: ' + JSON.stringify(execStats.body).slice(0, 600));

  // 报告统计
  const repStats = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/reports/stats', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  results.repStats = repStats;
  note('reports/stats: ' + JSON.stringify(repStats.body).slice(0, 400));

  fs.writeFileSync(EVID + '26-stats-compare.json', JSON.stringify(results, null, 2));
  await browser.close();
})();
