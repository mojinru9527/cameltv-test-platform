// B173-33: UI 任务列表 API（正确端点 /ui-automation/jobs 或 /ui-automation）
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
  await page.goto(BASE + '/uitest', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);

  // 从前端 api/uitest.ts 找端点
  const jobs = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/ui-automation', { headers: { 'X-Project-Id': '1' } });
    const b = await resp.json().catch(() => null);
    return { status: resp.status, data: b };
  });
  note('GET /ui-automation: ' + JSON.stringify(jobs.data ? { total: jobs.data.data && jobs.data.data.total, items: (jobs.data.data && jobs.data.data.items || []).map(j => ({ id: j.id, name: (j.name || '').slice(0, 25), status: j.status, last: j.last_result_at })) } : jobs.status));
  fs.writeFileSync(EVID + '33-ui-jobs.json', JSON.stringify(jobs, null, 2));
  await browser.close();
})();
