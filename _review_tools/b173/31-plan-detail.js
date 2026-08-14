// B173-31: 计划详情页执行按钮审查 + 执行历史列检查（C146-5/C147-2 复验）
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
  // 找一个有执行的计划（C170-1 生产登录态 UI = id 15）
  await page.goto(BASE + '/testplan/15', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  note('URL: ' + page.url());
  const txt = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync(EVID + '31-plan15-detail.txt', txt);
  // 找执行按钮
  const btns = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('button')).map(b => (b.innerText || '').trim()).filter(t => t && t.length < 30).slice(0, 60);
  });
  note('页面按钮: ' + JSON.stringify(btns));
  // 执行历史表格
  const tables = await page.locator('table').count();
  note('表格数: ' + tables);
  for (let i = 0; i < tables; i++) {
    const t = await page.locator('table').nth(i).innerText();
    if (t.includes('执行') || t.includes('pass') || t.includes('通过')) {
      note('表' + i + ': ' + t.replace(/\n/g, ' | ').slice(0, 500));
    }
  }
  await page.screenshot({ path: EVID + '31-plan15.png' }).catch(() => {});
  await browser.close();
})();
