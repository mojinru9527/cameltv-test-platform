// B173-34: UI 任务列表（/ui-tests 端点）
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

  const jobs = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/ui-tests', { headers: { 'X-Project-Id': '1' } });
    const b = await resp.json().catch(() => null);
    return { status: resp.status, data: b };
  });
  if (jobs.data && jobs.data.data) {
    const items = jobs.data.data.items || jobs.data.data;
    const list = (Array.isArray(items) ? items : []).map(j => ({
      id: j.id, name: (j.name || '').slice(0, 30), status: j.status, last_result: j.last_result, last_run_at: j.last_run_at, case_id: j.case_id, created: (j.created_at || '').slice(0, 16),
    }));
    note('UI 任务: ' + JSON.stringify(list, null, 1));
  } else {
    note('UI 任务响应: ' + JSON.stringify(jobs).slice(0, 300));
  }
  fs.writeFileSync(EVID + '34-ui-jobs.json', JSON.stringify(jobs, null, 2));
  await browser.close();
})();
