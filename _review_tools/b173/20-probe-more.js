// B173-20: ①确认环境残留并清理 ②系统管理/知识中心/发布包/Agent 快速探测
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

  // ===== 1) 环境列表完整文本 =====
  await page.goto(BASE + '/environment', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  const envText = await page.evaluate(() => document.body.innerText.slice(400, 2000));
  fs.writeFileSync(EVID + '20-env-full.txt', envText);
  note('环境页全文: ' + envText.replace(/\n/g, ' | ').slice(0, 500));
  const hasTmp = envText.includes('B173TMP');
  note('环境页含 B173TMP: ' + hasTmp);

  // ===== 2) 系统管理各 tab =====
  await page.goto(BASE + '/system', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const sysTabs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="tab"]')).map(t => t.innerText.trim()));
  note('系统管理 Tabs: ' + JSON.stringify(sysTabs));
  for (const t of ['角色管理', '审计日志', 'API Token', '邀请码']) {
    const tab = page.getByRole('tab', { name: t });
    if (await tab.count()) {
      await tab.first().click();
      await page.waitForTimeout(1200);
      const txt = await page.evaluate(() => document.body.innerText.slice(400, 1600));
      fs.writeFileSync(EVID + '20-system-' + t + '.txt', txt);
      note(t + ' Tab: ' + txt.replace(/\n/g, ' | ').slice(0, 250));
    }
  }

  // ===== 3) 知识中心 tab 结构 =====
  await page.goto(BASE + '/knowledge', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  const kTabs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="tab"]')).map(t => t.innerText.trim()));
  note('知识中心 Tabs: ' + JSON.stringify(kTabs));

  // ===== 4) 发布包详情 =====
  await page.goto(BASE + '/release-bundles', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const firstBundle = page.locator('tbody tr').first();
  if (await firstBundle.count()) {
    const txt = (await firstBundle.innerText()).replace(/\n/g, ' | ');
    note('发布包首行: ' + txt.slice(0, 200));
    await firstBundle.locator('a').first().click().catch(async () => {
      await firstBundle.click();
    });
    await page.waitForTimeout(2500);
    note('发布包详情 URL: ' + page.url());
    const detail = await page.evaluate(() => document.body.innerText.slice(400, 2000));
    fs.writeFileSync(EVID + '20-bundle-detail.txt', detail);
    note('发布包详情: ' + detail.replace(/\n/g, ' | ').slice(0, 400));
  }

  // ===== 5) Agent 工作台执行按钮 =====
  await page.goto(BASE + '/agent-workbench', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const agentExec = page.getByRole('button', { name: /^执行$/ }).first();
  if (await agentExec.count()) {
    await agentExec.click();
    await page.waitForTimeout(2500);
    const txt = await page.evaluate(() => document.body.innerText.slice(400, 2000));
    fs.writeFileSync(EVID + '20-agent-exec.txt', txt);
    note('Agent 执行后: ' + txt.replace(/\n/g, ' | ').slice(0, 350));
  }

  fs.writeFileSync(EVID + '20-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
