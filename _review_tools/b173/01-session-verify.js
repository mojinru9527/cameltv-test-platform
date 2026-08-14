// B173-01: 验证生产登录态 + 输出账号/项目/菜单信息
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv/test-platform-v2/config/runtime/sports-prod-storage-state.json';
const OUT = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: STATE, viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  const issues = [];
  page.on('console', m => { if (m.type() === 'error') issues.push({ t: 'console', text: m.text().slice(0, 300) }); });
  page.on('pageerror', e => issues.push({ t: 'pageerror', text: String(e).slice(0, 500) }));

  await page.goto(BASE + '/workbench', { waitUntil: 'networkidle', timeout: 60000 }).catch(e => console.log('goto err', e.message));
  await page.waitForTimeout(3000);
  console.log('URL:', page.url());
  console.log('TITLE:', await page.title());

  // 是否在登录页？
  if (page.url().includes('/login')) {
    console.log('SESSION: EXPIRED - redirected to login');
    await page.screenshot({ path: OUT + '01-login-page.png' });
  } else {
    console.log('SESSION: OK');
    // 抓取工作台文本摘要
    const body = await page.evaluate(() => document.body.innerText.slice(0, 3000));
    fs.writeFileSync(OUT + '01-workbench.txt', body);
    // 抓取菜单
    const menus = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a[href]'));
      return links.map(a => ({ href: a.getAttribute('href'), text: (a.innerText || '').trim().slice(0, 40) }));
    });
    fs.writeFileSync(OUT + '01-menus.json', JSON.stringify(menus, null, 2));
    console.log('MENUS:', JSON.stringify(menus.filter(m => m.href.startsWith('/')).slice(0, 40), null, 1));
    await page.screenshot({ path: OUT + '01-workbench.png', fullPage: false });
  }
  fs.writeFileSync(OUT + '01-console-issues.json', JSON.stringify(issues, null, 2));
  console.log('CONSOLE ISSUES:', issues.length);
  await browser.close();
})();
