// B173-36: 验证缺陷行删除按钮真实存在性（UI 报告对抗性修正复验）
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

  // 抓取首行所有按钮的 HTML（含 aria-label 检查）
  const rowBtns = await page.locator('tbody tr').first().evaluate(el => {
    return Array.from(el.querySelectorAll('button')).map(b => ({
      text: (b.innerText || '').trim(),
      aria: b.getAttribute('aria-label'),
      title: b.getAttribute('title'),
      html: b.outerHTML.slice(0, 300),
    }));
  });
  note('缺陷首行按钮: ' + JSON.stringify(rowBtns, null, 1));
  // 点击 aria-label 含"删除"的按钮
  const delBtn = page.locator('tbody tr').first().locator('[aria-label*="删除"]');
  note('删除按钮(aria) 数量=' + (await delBtn.count()));
  if (await delBtn.count()) {
    await delBtn.first().click();
    await page.waitForTimeout(800);
    const dlg = await page.evaluate(() => {
      const d = document.querySelector('[role="alertdialog"], [role="dialog"]');
      return d ? { role: d.getAttribute('role'), text: d.innerText.slice(0, 300) } : null;
    });
    note('点击后弹出: ' + JSON.stringify(dlg));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }
  await browser.close();
})();
