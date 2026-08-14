// B173-32: 验证 UI 任务"运行中"僵尸状态（双 worker 竞态的用户可见证据）
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
    const resp = await fetch('/api/v1/ui-automation/jobs', { headers: { 'X-Project-Id': '1' } });
    const b = await resp.json();
    return { status: resp.status, data: b.data };
  });
  if (jobs.data) {
    const items = jobs.data.items || jobs.data;
    for (const j of items) {
      note(`UI任务: id=${j.id} name=${(j.name || '').slice(0, 30)} status=${j.status} last=${j.last_result_at || '-'} runs=${(j.runs || []).length}`);
    }
  }
  fs.writeFileSync(EVID + '32-ui-jobs.json', JSON.stringify(jobs, null, 2));
  await browser.close();
})();
