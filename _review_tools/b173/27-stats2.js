// B173-27: 统计口径对比 v2 — 正确的端点路径
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

  const call = async (path) => {
    const r = await page.evaluate(async (p) => {
      const resp = await fetch(p, { headers: { 'X-Project-Id': '1' } });
      return { status: resp.status, body: await resp.json().catch(() => null) };
    }, path);
    return r;
  };

  // 工作台
  const dash = await call('/api/v1/dashboard/stats');
  note('dashboard/stats: ' + JSON.stringify(dash.body && dash.body.data).slice(0, 900));
  // 追溯覆盖
  const cov = await call('/api/v1/trace/coverage');
  note('trace/coverage: ' + JSON.stringify(cov.body && cov.body.data).slice(0, 900));
  // 计划统计
  const plans = await call('/api/v1/test-plans?page=1&page_size=1');
  note('test-plans meta: ' + JSON.stringify(plans.body && plans.body.data).slice(0, 500));
  // 执行总数（test_execution）
  const execs = await call('/api/v1/test-plans/18/executions?page=1&page_size=1');
  note('plan18 executions: ' + JSON.stringify(execs.body && execs.body.data).slice(0, 400));

  fs.writeFileSync(EVID + '27-stats2.json', JSON.stringify({ dash, cov, plans, execs }, null, 2));
  await browser.close();
})();
