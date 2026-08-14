// B173-29: 对比 API 数据 vs 页面渲染 — 确认渲染层 bug
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

  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);

  // 搜索"设置订阅金额为超大值"
  const sb = page.locator('input[placeholder="搜索标题/关键字"]').first();
  await sb.fill('设置订阅金额为超大值');
  await page.locator('button').filter({ hasText: /^搜索$/ }).first().click();
  await page.waitForTimeout(2500);
  const rows = await page.locator('tbody tr').count();
  note('搜索结果行=' + rows);
  if (rows > 0) {
    // 抓取该行完整渲染文本（前置条件列）
    const rowText = await page.locator('tbody tr').first().innerText();
    note('行渲染: ' + rowText.replace(/\n/g, ' | ').slice(0, 400));
    // 抓取前置条件单元格的 HTML
    const cellHtml = await page.locator('tbody tr').first().evaluate(el => {
      const tds = Array.from(el.querySelectorAll('td'));
      return tds.map(td => td.innerText.slice(0, 200));
    });
    note('各单元格: ' + JSON.stringify(cellHtml));
    fs.writeFileSync(EVID + '29-render-vs-api.json', JSON.stringify(cellHtml, null, 2));
  }

  // 搜索"APP启动检测到新版本"
  await sb.fill('APP启动检测到新版本');
  await page.locator('button').filter({ hasText: /^搜索$/ }).first().click();
  await page.waitForTimeout(2500);
  const rows2 = await page.locator('tbody tr').count();
  note('搜索2结果行=' + rows2);
  if (rows2 > 0) {
    const rowText2 = await page.locator('tbody tr').first().innerText();
    note('行2渲染: ' + rowText2.replace(/\n/g, ' | ').slice(0, 400));
  }

  await browser.close();
})();
