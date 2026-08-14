// B173-16: 缺陷管理深测 — 列表筛选 + 详情 + 状态流转 + 新建
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

  await page.goto(BASE + '/defect', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  note('defect loaded');

  // 新建缺陷对话框
  await page.getByRole('button', { name: /新建缺陷/ }).first().click();
  await page.waitForTimeout(1200);
  const dlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 1200) : 'NO'; });
  fs.writeFileSync(EVID + '16-defect-dialog.txt', dlg);
  note('新建缺陷对话框: ' + dlg.replace(/\n/g, ' | ').slice(0, 500));

  // 字段探测
  const fields = await page.evaluate(() => Array.from(document.querySelectorAll('[role="dialog"] input, [role="dialog"] select, [role="dialog"] textarea, [role="dialog"] [role="combobox"]')).map(i => ({
    tag: i.tagName, name: i.getAttribute('name'), id: i.id, ph: i.getAttribute('placeholder'), text: (i.innerText || '').trim().slice(0, 30),
  })));
  fs.writeFileSync(EVID + '16-defect-fields.json', JSON.stringify(fields, null, 2));
  note('字段: ' + JSON.stringify(fields.map(f => f.name || f.ph || f.text).filter(Boolean).slice(0, 15)));

  // 尝试创建（最小字段：标题+处理人）
  const title = 'B173TMP-缺陷-状态流转验证-' + (Date.now() % 100000);
  const titleInput = page.locator('[role="dialog"] input').first();
  await titleInput.fill(title);
  // 处理人选择
  const assignee = page.locator('[role="dialog"] [role="combobox"]').filter({ hasText: '选择' }).first();
  if (await assignee.count()) {
    await assignee.click();
    await page.waitForTimeout(800);
    const opt = page.locator('[role="option"]').first();
    if (await opt.count()) { note('处理人选项: ' + (await opt.innerText()).trim()); await opt.click(); }
  }
  await page.waitForTimeout(400);
  await page.screenshot({ path: EVID + '16-defect-filled.png' }).catch(() => {});
  await page.locator('[role="dialog"] button').filter({ hasText: /创建|保存/ }).first().click();
  await page.waitForTimeout(3000);
  note('创建缺陷后 dialog=' + (await page.locator('[role="dialog"]').count()));
  const posts = apiLog.filter(r => r.m === 'POST' && r.u.includes('defects'));
  note('POST defects: ' + JSON.stringify(posts.slice(-2)));

  // 搜索该缺陷
  const sb = page.locator('input[placeholder*="搜索"], input[placeholder*="编号"]').first();
  if (await sb.count()) {
    await sb.fill(title);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);
    const rows = await page.locator('tbody tr').count();
    note('搜索缺陷结果行=' + rows);
    if (rows > 0) {
      note('第一行: ' + (await page.locator('tbody tr').first().innerText()).replace(/\n/g, ' | ').slice(0, 250));
      // 打开详情
      const detailBtn = page.locator('tbody tr').first().getByRole('button', { name: /详情/ });
      if (await detailBtn.count()) {
        await detailBtn.first().click();
        await page.waitForTimeout(1500);
        const detailText = await page.evaluate(() => document.body.innerText.slice(0, 1500));
        fs.writeFileSync(EVID + '16-defect-detail.txt', detailText);
        note('详情页: ' + detailText.replace(/\n/g, ' | ').slice(0, 350));
        await page.goBack();
        await page.waitForTimeout(1500);
      }
    }
  }

  fs.writeFileSync(EVID + '16-defect-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
