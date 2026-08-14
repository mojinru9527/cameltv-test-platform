// B173-17: 环境/数据集/定时任务/通知/集成 模块 CRUD 深测 + 清理 B173TMP
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

  // ===== 1) 环境模块 =====
  await page.goto(BASE + '/environment', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  note('environment loaded');
  await page.getByRole('button', { name: /新建环境/ }).first().click();
  await page.waitForTimeout(1000);
  const envDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 600) : 'NO'; });
  fs.writeFileSync(EVID + '17-env-dialog.txt', envDlg);
  note('新建环境对话框: ' + envDlg.replace(/\n/g, ' | ').slice(0, 300));
  // 填写名称+类型
  const envName = 'B173TMP-环境-' + (Date.now() % 100000);
  const envInputs = page.locator('[role="dialog"] input');
  const en = await envInputs.count();
  for (let i = 0; i < en; i++) {
    const ph = await envInputs.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('名称')) { await envInputs.nth(i).fill(envName); note('环境名填入'); }
  }
  // 类型下拉选 test
  const typeCombo = page.locator('[role="dialog"] [role="combobox"]').first();
  if (await typeCombo.count()) {
    await typeCombo.click();
    await page.waitForTimeout(600);
    const opt = page.locator('[role="option"]').filter({ hasText: /测试|test/i }).first();
    if (await opt.count()) await opt.click();
    await page.waitForTimeout(300);
  }
  await page.locator('[role="dialog"] button').filter({ hasText: /保存|创建/ }).first().click();
  await page.waitForTimeout(2500);
  note('环境创建 POST: ' + JSON.stringify(apiLog.filter(r => r.m === 'POST' && r.u.includes('environments')).slice(-1)));

  // ===== 2) 数据集模块 =====
  await page.goto(BASE + '/dataset', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  note('dataset loaded: ' + (await page.locator('tbody tr').count()) + ' rows');
  await page.getByRole('button', { name: /新建数据集/ }).first().click();
  await page.waitForTimeout(1000);
  const dsDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 500) : 'NO'; });
  fs.writeFileSync(EVID + '17-dataset-dialog.txt', dsDlg);
  note('数据集对话框: ' + dsDlg.replace(/\n/g, ' | ').slice(0, 250));
  // 关闭
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  // ===== 3) 定时任务模块 =====
  await page.goto(BASE + '/schedule', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建调度/ }).first().click();
  await page.waitForTimeout(1000);
  const schDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 800) : 'NO'; });
  fs.writeFileSync(EVID + '17-schedule-dialog.txt', schDlg);
  note('新建调度对话框: ' + schDlg.replace(/\n/g, ' | ').slice(0, 400));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  // ===== 4) 通知配置 =====
  await page.goto(BASE + '/notify', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新增渠道/ }).first().click();
  await page.waitForTimeout(1000);
  const ntDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 700) : 'NO'; });
  fs.writeFileSync(EVID + '17-notify-dialog.txt', ntDlg);
  note('通知渠道对话框: ' + ntDlg.replace(/\n/g, ' | ').slice(0, 350));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  // ===== 5) 集成配置 =====
  await page.goto(BASE + '/integration', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建集成/ }).first().click();
  await page.waitForTimeout(1000);
  const igDlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 600) : 'NO'; });
  fs.writeFileSync(EVID + '17-integration-dialog.txt', igDlg);
  note('集成对话框: ' + igDlg.replace(/\n/g, ' | ').slice(0, 300));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  // ===== 6) 清理缺陷 B173TMP =====
  await page.goto(BASE + '/defect', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const sb = page.locator('input[placeholder*="搜索"]').first();
  if (await sb.count()) {
    await sb.fill('B173TMP');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);
    let rows = await page.locator('tbody tr').count();
    note('B173TMP 缺陷行=' + rows);
    let guard = 0;
    while (rows > 0 && guard < 5) {
      const row = page.locator('tbody tr').first();
      const delByAria = row.locator('[aria-label*="删除"]');
      if (await delByAria.count()) {
        await delByAria.first().click();
        await page.waitForTimeout(600);
        const confirm = page.locator('[role="alertdialog"] button').filter({ hasText: /^删除$/ });
        if (await confirm.count()) { await confirm.first().click(); await page.waitForTimeout(2000); }
        note('缺陷已删，剩余 ' + (await page.locator('tbody tr').count()));
      } else {
        note('缺陷行无删除按钮，尝试编辑');
        break;
      }
      await page.locator('button').filter({ hasText: /^搜索$/ }).first().click().catch(() => {});
      await page.waitForTimeout(1500);
      rows = await page.locator('tbody tr').count();
      guard++;
    }
  }

  fs.writeFileSync(EVID + '17-modules-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
