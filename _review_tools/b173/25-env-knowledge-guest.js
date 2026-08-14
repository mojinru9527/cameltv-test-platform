// B173-25: ①环境残留确认 ②知识中心 B173TMP 切片残留 ③登录/注册页 UI 检查
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
  const note = (m) => console.log('###', m);

  // ===== 1) 环境列表 API =====
  await page.goto(BASE + '/environment', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const envs = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/environments', { headers: { 'X-Project-Id': '1' } });
    const body = await resp.json().catch(() => null);
    return body;
  });
  note('环境列表: ' + JSON.stringify(envs).slice(0, 600));
  const envData = envs && envs.data;
  const items = Array.isArray(envData) ? envData : [];
  for (const e of items) {
    note('环境: id=' + e.id + ' name=' + e.name + ' type=' + e.env_type);
  }
  // 删除 B173TMP 环境
  for (const e of items) {
    if ((e.name || '').includes('B173TMP')) {
      const del = await page.evaluate(async (id) => {
        const resp = await fetch('/api/v1/environments/' + id, { method: 'DELETE', headers: { 'X-Project-Id': '1' } });
        return { status: resp.status, body: await resp.text().catch(() => '') };
      }, e.id);
      note('删除环境 #' + e.id + ': ' + JSON.stringify(del));
    }
  }

  // ===== 2) 知识中心搜索 B173TMP =====
  await page.goto(BASE + '/knowledge', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  const kSearch = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/knowledge/sources?keyword=B173TMP', { headers: { 'X-Project-Id': '1' } });
    return { status: resp.status, body: await resp.json().catch(() => null) };
  });
  note('知识源搜索 B173TMP: ' + JSON.stringify(kSearch).slice(0, 400));

  // ===== 3) 登录页 UI =====
  await page.goto(BASE + '/login', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const loginText = await page.evaluate(() => document.body.innerText.slice(0, 1500));
  fs.writeFileSync(EVID + '25-login.txt', loginText);
  note('登录页: ' + loginText.replace(/\n/g, ' | ').slice(0, 350));
  await page.screenshot({ path: EVID + '25-login.png' }).catch(() => {});

  // ===== 4) 注册页 UI =====
  await page.goto(BASE + '/register', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const regText = await page.evaluate(() => document.body.innerText.slice(0, 1500));
  fs.writeFileSync(EVID + '25-register.txt', regText);
  note('注册页: ' + regText.replace(/\n/g, ' | ').slice(0, 350));
  await page.screenshot({ path: EVID + '25-register.png' }).catch(() => {});

  // ===== 5) 未登录公开浏览首页 =====
  const ctx2 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page2 = await ctx2.newPage();
  await page2.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 60000 });
  await page2.waitForTimeout(2000);
  const homeText = await page2.evaluate(() => document.body.innerText.slice(0, 2000));
  fs.writeFileSync(EVID + '25-guest-home.txt', homeText);
  note('公开首页: ' + homeText.replace(/\n/g, ' | ').slice(0, 400));
  await page2.screenshot({ path: EVID + '25-guest-home.png' }).catch(() => {});
  await ctx2.close();

  await browser.close();
})();
