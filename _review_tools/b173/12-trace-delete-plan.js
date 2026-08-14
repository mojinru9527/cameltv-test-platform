// B173-12: 追查 ①用例删除为何无 DELETE ②计划创建为何失败
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
    if (u.includes('/api/')) apiLog.push({ m: resp.request().method(), u: decodeURIComponent(u.replace(BASE, '').split('?')[0]), s: resp.status(), t: Date.now() });
  });
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE ERR:', m.text().slice(0, 400)); });
  const note = (m) => console.log('###', m);

  // ===== 1) 删除流程逐帧观察 =====
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  // 搜索 B173TMP 用例
  const sb = page.locator('input[placeholder="搜索标题/关键字"]').first();
  await sb.fill('B173TMP-验证入库');
  await page.locator('button').filter({ hasText: /^搜索$/ }).first().click();
  await page.waitForTimeout(2500);
  const rows = await page.locator('tbody tr').count();
  note('搜索结果行=' + rows);
  if (rows > 0) {
    // 完整 dump 行内 DOM（含按钮）
    const rowHtml = await page.locator('tbody tr').first().evaluate(el => {
      return Array.from(el.querySelectorAll('button')).map(b => ({
        text: (b.innerText || '').trim().slice(0, 20),
        aria: b.getAttribute('aria-label'),
        title: b.getAttribute('title'),
        cls: (b.className || '').slice(0, 80),
      }));
    });
    note('行按钮详情: ' + JSON.stringify(rowHtml, null, 1));
    // 尝试点击"删除"图标按钮
    const delBtn = page.locator('tbody tr').first().getByRole('button', { name: /删除/ });
    note('删除按钮(role) 数量=' + (await delBtn.count()));
    if (await delBtn.count()) {
      await delBtn.first().click();
      await page.waitForTimeout(800);
      // 观察弹出层
      const overlays = await page.evaluate(() => {
        const dlg = document.querySelector('[role="alertdialog"], [role="dialog"]');
        return dlg ? { text: dlg.innerText.slice(0, 300), role: dlg.getAttribute('role') } : null;
      });
      note('点击删除后弹出: ' + JSON.stringify(overlays));
      // 点击确认删除
      const confirmBtns = page.locator('[role="alertdialog"] button, [role="dialog"] button');
      const btns = await confirmBtns.allInnerTexts();
      note('弹出层按钮: ' + JSON.stringify(btns));
      // 用精确文本点"删除"
      const realDel = page.locator('[role="alertdialog"] button').filter({ hasText: /^删除$/ });
      if (await realDel.count()) {
        await realDel.first().click();
        await page.waitForTimeout(2500);
        note('确认删除后 DELETE 请求: ' + JSON.stringify(apiLog.filter(r => r.m === 'DELETE')));
      }
    }
  }

  // ===== 2) 计划创建逐帧观察 =====
  await page.goto(BASE + '/testplan', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建计划/ }).first().click();
  await page.waitForTimeout(1000);
  // dump 表单字段
  const fields = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[role="dialog"] input, [role="dialog"] textarea, [role="dialog"] [role="combobox"]')).map(i => ({
      tag: i.tagName, name: i.getAttribute('name'), ph: i.getAttribute('placeholder'), text: (i.innerText || '').trim().slice(0, 20),
      disabled: i.disabled || i.getAttribute('aria-disabled'),
    }));
  });
  note('计划表单字段: ' + JSON.stringify(fields, null, 1));
  // 填名称
  const planTitle = 'B173TMP-计划追查-' + (Date.now() % 1000000);
  const pInputs = page.locator('[role="dialog"] input');
  const pn = await pInputs.count();
  for (let i = 0; i < pn; i++) {
    const ph = await pInputs.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('名称')) { await pInputs.nth(i).fill(planTitle); note('名称已填: ' + ph); }
  }
  await page.waitForTimeout(500);
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(3000);
  const errs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="dialog"] [role="alert"], [role="dialog"] .text-destructive')).map(e => e.innerText.trim().slice(0, 120)));
  note('保存后错误提示: ' + JSON.stringify(errs));
  note('POST test-plans 请求: ' + JSON.stringify(apiLog.filter(r => r.m === 'POST' && r.u.includes('test-plans'))));
  note('dialog 数=' + (await page.locator('[role="dialog"]').count()));
  // dump dialog 当前内容
  const dlgText = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 600) : 'NO'; });
  note('dialog 内容: ' + dlgText.replace(/\n/g, ' | ').slice(0, 400));

  fs.writeFileSync(EVID + '12-trace-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
