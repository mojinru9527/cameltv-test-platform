// B173-24: 通过列表 API 找到 B173TMP 缺陷真实 ID 并删除
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
  await page.goto(BASE + '/defect', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);

  // 调列表 API 找 id
  const list = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/defects?page=1&page_size=50&keyword=B173TMP', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  note('缺陷列表(B173TMP): ' + JSON.stringify(list).slice(0, 800));

  let targetId = null;
  if (list.body && list.body.data) {
    const items = Array.isArray(list.body.data) ? list.body.data : (list.body.data.items || list.body.data.records || []);
    for (const it of items) {
      note('候选: id=' + it.id + ' 编号=' + it.defect_no + ' 标题=' + (it.title || '').slice(0, 40));
      if ((it.title || '').includes('B173TMP') || (it.defect_no || '').includes('B173TMP')) targetId = it.id;
    }
  }
  if (targetId) {
    const del = await page.evaluate(async (id) => {
      const resp = await fetch('/api/v1/defects/' + id, { method: 'DELETE', headers: { 'X-Project-Id': '1' } });
      return { status: resp.status, body: await resp.text().catch(() => '') };
    }, targetId);
    note('删除缺陷 #' + targetId + ': ' + JSON.stringify(del));
  } else {
    note('未找到 B173TMP 缺陷 ID');
  }

  // 复验
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const body = await page.evaluate(() => document.body.innerText);
  note('缺陷列表仍含 B173TMP: ' + body.includes('B173TMP'));
  await browser.close();
})();
