// B173-08: 精确探测新建用例对话框完整结构（按钮/下拉/必填校验）
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
    if (u.includes('/api/')) apiLog.push({ m: resp.request().method(), u: u.replace(BASE, '').split('?')[0], s: resp.status() });
  });

  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // 精确搜索防抖测试：记录每个按键后的请求时间
  const searchBox = page.locator('input[placeholder="搜索标题/关键字"]').first();
  const t0 = Date.now();
  const searchEvents = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('/api/test-cases') && resp.request().method() === 'GET') {
      searchEvents.push({ t: Date.now() - t0, status: resp.status() });
    }
  });
  for (const ch of 'UGC') {
    await searchBox.press(ch);
    await page.waitForTimeout(150);
  }
  await page.waitForTimeout(3000);
  console.log('搜索防抖事件:', JSON.stringify(searchEvents));
  await searchBox.fill('');
  await page.waitForTimeout(1000);

  // 打开新建用例对话框
  await page.getByRole('button', { name: /新建用例/ }).first().click();
  await page.waitForTimeout(1200);

  // 列出 dialog 内所有可见按钮及文本
  const btns = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[role="dialog"] button'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({ text: (b.innerText || '').trim().slice(0, 40), aria: b.getAttribute('aria-label'), disabled: b.disabled }));
  });
  console.log('DIALOG BUTTONS:', JSON.stringify(btns, null, 1));
  fs.writeFileSync(EVID + '08-dialog-buttons.json', JSON.stringify(btns, null, 2));

  // 探测所有 select/combobox
  const combos = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[role="dialog"] [role="combobox"], [role="dialog"] [data-slot="select-trigger"]'))
      .map(c => ({ text: (c.innerText || '').trim().slice(0, 60) }));
  });
  console.log('COMBOBOXES:', JSON.stringify(combos, null, 1));

  // 不填任何必填直接点保存 → 观察校验
  const saveBtn = page.locator('[role="dialog"] button').filter({ hasText: /保存/ });
  console.log('SAVE BTN COUNT:', await saveBtn.count());
  if (await saveBtn.count()) {
    await saveBtn.first().click().catch(e => console.log('save click err', e.message.slice(0, 100)));
    await page.waitForTimeout(1500);
    const msgs = await page.evaluate(() => {
      const errs = Array.from(document.querySelectorAll('[role="dialog"] [role="alert"], [role="dialog"] .text-destructive, [role="dialog"] p')).map(e => e.innerText.trim()).filter(t => t && t.length < 120);
      return errs.slice(0, 15);
    });
    console.log('校验提示:', JSON.stringify(msgs, null, 1));
    // 对话框是否还开着
    console.log('DIALOG STILL OPEN:', await page.locator('[role="dialog"]').count());
  }

  // 检查 dialog 内是否有滚动（页面 900px 高，dialog 可能超长）
  const dims = await page.evaluate(() => {
    const d = document.querySelector('[role="dialog"]');
    if (!d) return null;
    const r = d.getBoundingClientRect();
    return { top: r.top, height: r.height, viewportH: window.innerHeight, scrollH: d.scrollHeight, clientH: d.clientHeight, overflow: d.scrollHeight > d.clientHeight };
  });
  console.log('DIALOG DIMS:', JSON.stringify(dims));

  // 尝试填标题后保存，观察是否成功（此时不选模块）
  await page.locator('[role="dialog"] input[name="title"]').fill('B173TMP-必填探测-' + Date.now() % 100000);
  await saveBtn.first().click().catch(() => {});
  await page.waitForTimeout(2500);
  console.log('仅填标题保存后 dialog=', await page.locator('[role="dialog"]').count());
  const afterMsgs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="alert"]')).map(e => e.innerText.trim().slice(0, 100)));
  console.log('保存后提示:', JSON.stringify(afterMsgs));

  fs.writeFileSync(EVID + '08-dialog-log.json', JSON.stringify({ apiLog }, null, 2));
  await browser.close();
})();
