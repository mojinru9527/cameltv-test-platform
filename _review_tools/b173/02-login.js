// B173-02: 重新登录生产平台并保存 storage state
// 凭据从本地未跟踪文件读取（F:/CamelTv/_review_tools/.prod-credentials.env），禁止硬编码提交
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = 'https://cameltv-test-platform1.vercel.app';
const credFile = 'F:/CamelTv/_review_tools/.prod-credentials.env';
const creds = {};
if (fs.existsSync(credFile)) {
  for (const line of fs.readFileSync(credFile, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) creds[m[1]] = m[2].trim();
  }
}
const USER = creds.TP_ADMIN_USERNAME || 'sportsadmin';
const PASS = creds.TP_ADMIN_PASSWORD || '';
const OUT = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';
const STATE_OUT = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  const issues = [];
  page.on('console', m => { if (m.type() === 'error') issues.push({ t: 'console', text: m.text().slice(0, 300) }); });
  page.on('pageerror', e => issues.push({ t: 'pageerror', text: String(e).slice(0, 500) }));

  await page.goto(BASE + '/login', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  console.log('LOGIN URL:', page.url());
  // 打印登录页表单结构
  const form = await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input')).map(i => ({ name: i.name, id: i.id, type: i.type, ph: i.placeholder }));
    const buttons = Array.from(document.querySelectorAll('button')).map(b => (b.innerText || b.getAttribute('aria-label') || '').trim().slice(0, 30));
    return { inputs, buttons };
  });
  console.log('FORM:', JSON.stringify(form, null, 1));

  // 尝试填充并登录（探测选择器）
  let loggedIn = false;
  const tryFill = async (userSel, passSel, btnSel) => {
    try {
      await page.fill(userSel, USER);
      await page.fill(passSel, PASS);
      await page.click(btnSel);
      await page.waitForTimeout(4000);
      loggedIn = !page.url().includes('/login');
      console.log('TRY', userSel, '->', page.url(), 'loggedIn=', loggedIn);
    } catch (e) {
      console.log('TRY FAIL', userSel, e.message.slice(0, 120));
    }
  };
  if (form.inputs.length >= 2) {
    const i1 = form.inputs[0], i2 = form.inputs[1];
    const sel1 = i1.id ? `#${i1.id}` : (i1.name ? `input[name="${i1.name}"]` : 'input[type="text"], input[type="email"], input:not([type="password"])');
    const sel2 = i2.id ? `#${i2.id}` : (i2.name ? `input[name="${i2.name}"]` : 'input[type="password"]');
    await tryFill(sel1, sel2, 'button[type="submit"]');
  }
  if (!loggedIn) {
    // 备选：按顺序填充所有 input
    await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const inputs = page.locator('input');
    const n = await inputs.count();
    console.log('INPUT COUNT:', n);
    if (n >= 2) {
      await inputs.nth(0).fill(USER);
      await inputs.nth(1).fill(PASS);
      const btns = page.locator('button');
      const bn = await btns.count();
      for (let i = 0; i < bn; i++) {
        const t = (await btns.nth(i).innerText().catch(() => '')).trim();
        if (t.includes('登录') || t.includes('登 录')) { await btns.nth(i).click(); break; }
      }
      await page.waitForTimeout(4000);
      loggedIn = !page.url().includes('/login');
      console.log('ALT: URL=', page.url(), 'loggedIn=', loggedIn);
    }
  }

  await page.screenshot({ path: OUT + '02-after-login.png' });
  if (loggedIn) {
    await context.storageState({ path: STATE_OUT });
    console.log('STATE SAVED to', STATE_OUT);
    const body = await page.evaluate(() => document.body.innerText.slice(0, 1200));
    fs.writeFileSync(OUT + '02-after-login.txt', body);
  } else {
    const body = await page.evaluate(() => document.body.innerText.slice(0, 1500));
    fs.writeFileSync(OUT + '02-login-fail.txt', body);
    console.log('LOGIN FAILED. Page text saved.');
  }
  fs.writeFileSync(OUT + '02-issues.json', JSON.stringify(issues, null, 2));
  console.log('CONSOLE ISSUES:', issues.length);
  await browser.close();
})();
