// B173-37: 点击缺陷行第4个裸图标按钮，验证是否为删除确认
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

  // 点击首行第 4 个按钮（裸图标）
  const btns = page.locator('tbody tr').first().locator('button');
  note('首行按钮数=' + (await btns.count()));
  if (await btns.count() >= 4) {
    await btns.nth(3).click();
    await page.waitForTimeout(1000);
    const dlg = await page.evaluate(() => {
      const d = document.querySelector('[role="alertdialog"]');
      return d ? { role: d.getAttribute('role'), text: d.innerText.slice(0, 400) } : null;
    });
    note('弹出: ' + JSON.stringify(dlg));
    fs.writeFileSync(EVID + '37-defect-del-dialog.txt', JSON.stringify(dlg, null, 2));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }
  await browser.close();
})();
