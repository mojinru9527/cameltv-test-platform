// B173-09: 页面初始加载请求明细 — 量化 testcase 页 4 次 GET 是否冗余
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
  const reqs = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('/api/')) reqs.push({ m: resp.request().method(), u: decodeURIComponent(u.replace(BASE, '')), s: resp.status(), t: Date.now() });
  });
  const t0 = Date.now();
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  reqs.forEach(r => r.dt = r.t - t0);
  fs.writeFileSync(EVID + '09-testcase-load-requests.json', JSON.stringify(reqs, null, 2));
  // 分组统计
  const byUrl = {};
  reqs.forEach(r => {
    const k = r.m + ' ' + r.u.split('?')[0];
    byUrl[k] = (byUrl[k] || 0) + 1;
  });
  console.log('=== 按URL分组 ===');
  Object.entries(byUrl).forEach(([k, c]) => console.log(`${c}x ${k}`));
  console.log('TOTAL:', reqs.length);
  await browser.close();
})();
