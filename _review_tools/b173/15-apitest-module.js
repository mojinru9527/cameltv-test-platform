// B173-15: 接口测试模块深测 — 快速调试 + 接口用例 + 执行任务 + 导入
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
  const apiLog = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('/api/')) apiLog.push({ m: resp.request().method(), u: decodeURIComponent(u.replace(BASE, '').split('?')[0]), s: resp.status() });
  });
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE ERR:', m.text().slice(0, 400)); });
  const note = (m) => console.log('###', m);

  await page.goto(BASE + '/apitest', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  note('apitest loaded');

  // Tab 结构
  const tabs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="tab"]')).map(t => t.innerText.trim()));
  note('Tabs: ' + JSON.stringify(tabs));

  // ===== 快速调试 Tab =====
  const debugTab = page.getByRole('tab', { name: '快速调试' });
  if (await debugTab.count()) {
    await debugTab.first().click();
    await page.waitForTimeout(1500);
    const debugText = await page.evaluate(() => document.body.innerText.slice(0, 1500));
    fs.writeFileSync(EVID + '15-debug-tab.txt', debugText);
    note('快速调试页文本: ' + debugText.replace(/\n/g, ' | ').slice(0, 400));
  }

  // ===== 接口用例 Tab =====
  const caseTab = page.getByRole('tab', { name: '接口用例' });
  if (await caseTab.count()) {
    await caseTab.first().click();
    await page.waitForTimeout(2000);
    const caseText = await page.evaluate(() => document.body.innerText.slice(0, 1200));
    fs.writeFileSync(EVID + '15-apicase-tab.txt', caseText);
    note('接口用例Tab: ' + caseText.replace(/\n/g, ' | ').slice(0, 300));
  }

  // ===== 执行任务 Tab =====
  const taskTab = page.getByRole('tab', { name: '执行任务' });
  if (await taskTab.count()) {
    await taskTab.first().click();
    await page.waitForTimeout(2000);
    const taskText = await page.evaluate(() => document.body.innerText.slice(0, 1500));
    fs.writeFileSync(EVID + '15-task-tab.txt', taskText);
    note('执行任务Tab: ' + taskText.replace(/\n/g, ' | ').slice(0, 400));
  }

  // ===== 导入接口 Tab（探测导入对话框）=====
  const importBtn = page.getByRole('button', { name: /导入接口/ });
  if (await importBtn.count()) {
    await importBtn.first().click();
    await page.waitForTimeout(1200);
    const dlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 800) : 'NO DIALOG'; });
    fs.writeFileSync(EVID + '15-import-dialog.txt', dlg);
    note('导入对话框: ' + dlg.replace(/\n/g, ' | ').slice(0, 350));
    // 关闭
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
  }

  fs.writeFileSync(EVID + '15-apitest-log.json', JSON.stringify(apiLog, null, 2));
  const dup = {};
  apiLog.filter(r => r.m === 'GET').forEach(r => { const k = r.m + r.u; dup[k] = (dup[k] || 0) + 1; });
  note('GET 重复: ' + JSON.stringify(Object.entries(dup).filter(([, c]) => c > 1)));
  await browser.close();
})();
