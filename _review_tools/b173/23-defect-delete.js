// B173-23: 用带项目头的 API 删除 B173TMP 缺陷
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
  // 获取当前项目 id
  const projInfo = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/projects', { headers: { 'X-Project-Id': '' } });
    const body = await resp.json().catch(() => null);
    return { status: resp.status, data: body };
  });
  note('项目列表: ' + JSON.stringify(projInfo).slice(0, 400));
  // 从 /auth/me 获取当前项目
  const me = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/auth/me');
    return await resp.json().catch(() => null);
  });
  note('auth/me: ' + JSON.stringify(me).slice(0, 400));

  // 查找 B173TMP 缺陷行并提取编号
  const rows = await page.locator('tbody tr').all();
  for (const row of rows) {
    const txt = await row.innerText();
    if (txt.includes('B173TMP')) {
      const idText = txt.split('\t')[0].trim();
      note('待删缺陷: ' + idText);
      const del = await page.evaluate(async (defId) => {
        const resp = await fetch('/api/v1/defects/' + defId, { method: 'DELETE', headers: { 'X-Project-Id': '1' } });
        return { status: resp.status, body: await resp.text().catch(() => '') };
      }, idText);
      note('带项目头删除: ' + JSON.stringify(del));
      await page.waitForTimeout(1500);
    }
  }

  // 复验缺陷列表
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const body = await page.evaluate(() => document.body.innerText);
  note('缺陷列表仍含 B173TMP: ' + body.includes('B173TMP'));

  await browser.close();
})();
