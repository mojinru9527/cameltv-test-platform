// B173-14: 清理 B173TMP 测试数据 + 验证计划删除
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
  const note = (m) => console.log('###', m);

  // ===== 1) 删除测试计划（B173TMP-计划复验-*）=====
  await page.goto(BASE + '/testplan', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  // 搜索计划
  const sb = page.locator('input[placeholder]').first();
  await sb.fill('B173TMP-计划复验');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(2000);
  const rows = await page.locator('tbody tr').count();
  note('计划搜索结果行=' + rows);
  if (rows > 0) {
    const firstRow = page.locator('tbody tr').first();
    const btns = await firstRow.locator('button').allInnerTexts();
    note('计划行按钮: ' + JSON.stringify(btns));
    // dump 行按钮 aria
    const btnAria = await firstRow.evaluate(el => Array.from(el.querySelectorAll('button')).map(b => b.getAttribute('aria-label') || (b.innerText||'').trim()));
    note('计划行按钮aria: ' + JSON.stringify(btnAria));
    // 找删除按钮
    const delBtn = firstRow.locator('button').filter({ has: page.locator('svg') }).last();
    // 尝试通过 aria-label 删除
    const delByAria = firstRow.locator('[aria-label*="删除"]');
    if (await delByAria.count()) {
      await delByAria.first().click();
      await page.waitForTimeout(800);
      const confirm = page.locator('[role="alertdialog"] button').filter({ hasText: /^删除$/ });
      if (await confirm.count()) { await confirm.first().click(); await page.waitForTimeout(2500); }
      note('计划删除后 DELETE: ' + JSON.stringify(apiLog.filter(r => r.m === 'DELETE' && r.u.includes('plan'))));
    } else {
      note('计划行无删除按钮 aria — 尝试查看详情');
      await firstRow.locator('a, button').first().click().catch(() => {});
      await page.waitForTimeout(2000);
      note('跳转后 URL: ' + page.url());
    }
  }

  // ===== 2) 清理 B173TMP 用例 =====
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const sb2 = page.locator('input[placeholder="搜索标题/关键字"]').first();
  await sb2.fill('B173TMP');
  await page.locator('button').filter({ hasText: /^搜索$/ }).first().click();
  await page.waitForTimeout(2500);
  let caseRows = await page.locator('tbody tr').count();
  note('B173TMP 用例结果行=' + caseRows);
  // 循环删除直到没有
  let guard = 0;
  while (caseRows > 0 && guard < 10) {
    const row = page.locator('tbody tr').first();
    const delByAria = row.locator('[aria-label*="删除"]');
    if (await delByAria.count()) {
      await delByAria.first().click();
      await page.waitForTimeout(600);
      const confirm = page.locator('[role="alertdialog"] button').filter({ hasText: /^删除$/ });
      if (await confirm.count()) { await confirm.first().click(); await page.waitForTimeout(2000); }
      note('已删一条，剩余: ' + (await page.locator('tbody tr').count()));
    } else break;
    // 重新搜索
    await page.locator('button').filter({ hasText: /^搜索$/ }).first().click();
    await page.waitForTimeout(2000);
    caseRows = await page.locator('tbody tr').count();
    guard++;
  }
  note('清理完成，剩余行=' + caseRows);

  fs.writeFileSync(EVID + '14-cleanup-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
