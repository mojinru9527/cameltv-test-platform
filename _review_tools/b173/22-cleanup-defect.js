// B173-22: ①通过 API 清理 B173TMP 缺陷（前端无删除入口）②角色管理/邀请码 tab 复测
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

  // ===== 1) 用页面上下文直接调 API 删除缺陷 =====
  await page.goto(BASE + '/defect', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  // 查找缺陷 ID：从列表行找 DEF 编号
  const rows = await page.locator('tbody tr').all();
  for (const row of rows) {
    const txt = await row.innerText();
    if (txt.includes('B173TMP')) {
      const idText = txt.split('\t')[0].trim();
      note('找到 B173TMP 缺陷: ' + idText + ' | ' + txt.slice(0, 100).replace(/\n/g, ' '));
      // 用 fetch 直接删除（same-origin 带 cookie）
      const del = await page.evaluate(async (defId) => {
        const resp = await fetch('/api/v1/defects/' + defId, { method: 'DELETE' });
        return { status: resp.status, body: await resp.text().catch(() => '') };
      }, idText);
      note('API 删除结果: ' + JSON.stringify(del));
      await page.waitForTimeout(1000);
    }
  }

  // ===== 2) 角色管理 tab 复测（截图看是否渲染）=====
  await page.goto(BASE + '/system', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.getByRole('tab', { name: '角色管理' }).click();
  await page.waitForTimeout(3000);
  // 全文本
  const roleFull = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync(EVID + '22-roles-full.txt', roleFull);
  note('角色管理全文长度=' + roleFull.length + ' 含角色=' + roleFull.includes('admin') + ' 含超级管理员=' + roleFull.includes('超级管理员'));
  await page.screenshot({ path: EVID + '22-roles.png' }).catch(() => {});
  // 检查是否有表格
  const hasTable = await page.locator('table').count();
  note('角色管理 table 数=' + hasTable);
  if (hasTable > 0) {
    note('角色表格: ' + (await page.locator('table').first().innerText()).replace(/\n/g, ' | ').slice(0, 300));
  }

  // 邀请码 tab
  await page.getByRole('tab', { name: '邀请码' }).click();
  await page.waitForTimeout(3000);
  const invFull = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync(EVID + '22-invite-full.txt', invFull);
  note('邀请码全文长度=' + invFull.length + ' 含邀请=' + invFull.includes('邀请'));
  const invTable = await page.locator('table').count();
  note('邀请码 table 数=' + invTable);
  if (invTable > 0) {
    note('邀请码表格: ' + (await page.locator('table').first().innerText()).replace(/\n/g, ' | ').slice(0, 300));
  }
  await page.screenshot({ path: EVID + '22-invite.png' }).catch(() => {});

  await browser.close();
})();
