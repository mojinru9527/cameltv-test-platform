// B173-30: 验证已删缺陷在知识中心的残留展示（确认用户可见性）
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
  await page.goto(BASE + '/knowledge', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);

  // 项目知识 tab 搜索 B173TMP
  await page.getByRole('tab', { name: '项目知识' }).first().click().catch(() => {});
  await page.waitForTimeout(1500);
  const body = await page.evaluate(() => document.body.innerText);
  note('知识中心-项目知识 含 B173TMP: ' + body.includes('B173TMP'));
  // 搜索框
  const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="检索"]').first();
  if (await searchInput.count()) {
    await searchInput.fill('B173TMP');
    await page.keyboard.press('Enter').catch(() => {});
    await page.waitForTimeout(2000);
    const body2 = await page.evaluate(() => document.body.innerText.slice(0, 1500));
    fs.writeFileSync(EVID + '30-knowledge-residue.txt', body2);
    note('搜索 B173TMP 结果: ' + body2.replace(/\n/g, ' | ').slice(200, 700));
  }

  await browser.close();
})();
