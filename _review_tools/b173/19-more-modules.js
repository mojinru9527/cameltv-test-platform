// B173-19: 清理 B173TMP 环境 + 需求文档模块深测 + UI自动化 + 报告生成
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

  // ===== 1) 清理 B173TMP 环境 =====
  await page.goto(BASE + '/environment', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const envRows = await page.locator('tbody tr').count();
  note('环境列表行=' + envRows);
  for (let i = 0; i < envRows; i++) {
    const row = page.locator('tbody tr').nth(i);
    const txt = await row.innerText();
    if (txt.includes('B173TMP')) {
      note('找到 B173TMP 环境行: ' + txt.slice(0, 80).replace(/\n/g, ' | '));
      const del = row.locator('[aria-label*="删除"]');
      if (await del.count()) {
        await del.first().click();
        await page.waitForTimeout(600);
        const confirm = page.locator('[role="alertdialog"] button').filter({ hasText: /^删除$/ });
        if (await confirm.count()) { await confirm.first().click(); await page.waitForTimeout(2000); }
        note('环境删除 DELETE: ' + JSON.stringify(apiLog.filter(r => r.m === 'DELETE' && r.u.includes('environments'))));
      }
    }
  }

  // ===== 2) 需求文档模块 =====
  await page.goto(BASE + '/requirement', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  note('requirement loaded');
  // 需求列表行
  const reqRows = await page.locator('tbody tr, table tr').count();
  note('需求表格行=' + reqRows);
  // 探测需求行操作
  const firstReq = page.locator('tbody tr').first();
  if (await firstReq.count()) {
    const btnAria = await firstReq.evaluate(el => Array.from(el.querySelectorAll('button')).map(b => b.getAttribute('aria-label') || (b.innerText || '').trim()).filter(Boolean));
    note('需求首行按钮: ' + JSON.stringify(btnAria.slice(0, 12)));
    const txt = (await firstReq.innerText()).replace(/\n/g, ' | ').slice(0, 200);
    note('需求首行: ' + txt);
  }

  // ===== 3) UI 自动化模块 =====
  await page.goto(BASE + '/uitest', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  note('uitest loaded');
  // 用例/脚本 tab
  const tab2 = page.getByRole('tab', { name: /用例 \/ 脚本/ });
  if (await tab2.count()) {
    await tab2.first().click();
    await page.waitForTimeout(1500);
    const txt = await page.evaluate(() => document.body.innerText.slice(400, 2000));
    fs.writeFileSync(EVID + '19-uitest-cases.txt', txt);
    note('用例/脚本 Tab: ' + txt.replace(/\n/g, ' | ').slice(0, 300));
  }
  // 新建任务对话框
  await page.getByRole('button', { name: /新建任务/ }).first().click().catch(() => {});
  await page.waitForTimeout(1200);
  const uiDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 800) : 'NO'; });
  fs.writeFileSync(EVID + '19-uitest-dialog.txt', uiDlg);
  note('UI 任务对话框: ' + uiDlg.replace(/\n/g, ' | ').slice(0, 400));
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(500);

  // ===== 4) 报告生成 =====
  await page.goto(BASE + '/report', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /生成报告/ }).first().click().catch(() => {});
  await page.waitForTimeout(1200);
  const rpDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 800) : 'NO'; });
  fs.writeFileSync(EVID + '19-report-dialog.txt', rpDlg);
  note('报告对话框: ' + rpDlg.replace(/\n/g, ' | ').slice(0, 400));
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(500);

  fs.writeFileSync(EVID + '19-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
