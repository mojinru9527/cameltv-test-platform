// B173-13: 复验计划创建 Bug — 检查 name 输入值是否真正绑定 + 保存逻辑
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
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE ERR:', m.text().slice(0, 500)); });
  const note = (m) => console.log('###', m);

  await page.goto(BASE + '/testplan', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建计划/ }).first().click();
  await page.waitForTimeout(1000);

  const planTitle = 'B173TMP-计划复验-' + (Date.now() % 1000000);
  // 精确填充 name input
  const nameInput = page.locator('[role="dialog"] input[name="name"]');
  await nameInput.fill(planTitle);
  await page.waitForTimeout(300);
  // 验证输入值已写入 DOM
  const val = await nameInput.inputValue();
  note('name input value = "' + val + '"');

  // 检查 React 是否注册了 onChange（通过 dispatch 模拟真实用户输入）
  await nameInput.press('End');
  await nameInput.press(' ');
  await nameInput.press('Backspace');
  await page.waitForTimeout(300);
  const val2 = await nameInput.inputValue();
  note('after keypress value = "' + val2 + '"');

  // 点击保存
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(3000);
  const errs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="dialog"] [role="alert"]')).map(e => e.innerText.trim().slice(0, 100)));
  note('保存后错误: ' + JSON.stringify(errs));
  note('POST: ' + JSON.stringify(apiLog.filter(r => r.m === 'POST' && r.u.includes('plan'))));
  note('dialog=' + (await page.locator('[role="dialog"]').count()));

  // 再试一次：改用 type 模拟逐字符输入
  await nameInput.fill('');
  await nameInput.type(planTitle + 'B', { delay: 50 });
  await page.waitForTimeout(300);
  const val3 = await nameInput.inputValue();
  note('type 后 value = "' + val3 + '"');
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(3000);
  const errs2 = await page.evaluate(() => Array.from(document.querySelectorAll('[role="dialog"] [role="alert"]')).map(e => e.innerText.trim().slice(0, 100)));
  note('第二次保存错误: ' + JSON.stringify(errs2));
  note('POST2: ' + JSON.stringify(apiLog.filter(r => r.m === 'POST' && r.u.includes('plan'))));
  note('dialog2=' + (await page.locator('[role="dialog"]').count()));

  fs.writeFileSync(EVID + '13-plan-bug-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
