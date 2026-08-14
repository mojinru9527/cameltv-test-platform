// B173-06b: 探测 testcase 页面输入框与按钮结构
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
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  const info = await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input, textarea')).map(i => ({
      tag: i.tagName, name: i.getAttribute('name'), id: i.id, ph: i.getAttribute('placeholder'), type: i.type,
      cls: (i.className || '').slice(0, 60),
    }));
    const buttons = Array.from(document.querySelectorAll('button')).map(b => (b.innerText || '').trim().slice(0, 30)).filter(Boolean).slice(0, 40);
    return { inputs, buttons };
  });
  fs.writeFileSync(EVID + '06b-testcase-dom.json', JSON.stringify(info, null, 2));
  console.log(JSON.stringify(info, null, 1));
  await browser.close();
})();
