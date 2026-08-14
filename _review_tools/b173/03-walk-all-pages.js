// B173-03: 全站页面遍历 — 每个页面抓取 截图/文本/API请求日志(含重复统计)/控制台错误/加载耗时
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';
const EVID = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';
const SHOTS = EVID + 'pages/';

const ROUTES = [
  { path: '/workbench', name: 'workbench' },
  { path: '/trace', name: 'trace' },
  { path: '/requirement', name: 'requirement' },
  { path: '/testcase', name: 'testcase' },
  { path: '/testplan', name: 'testplan' },
  { path: '/mindmap', name: 'mindmap' },
  { path: '/apitest', name: 'apitest' },
  { path: '/uitest', name: 'uitest' },
  { path: '/playground', name: 'playground' },
  { path: '/schedule', name: 'schedule' },
  { path: '/report', name: 'report' },
  { path: '/system', name: 'system' },
  { path: '/my-projects', name: 'my-projects' },
  { path: '/defect', name: 'defect' },
  { path: '/dataset', name: 'dataset' },
  { path: '/integration', name: 'integration' },
  { path: '/notify', name: 'notify' },
  { path: '/environment', name: 'environment' },
  { path: '/agent-workbench', name: 'agent-workbench' },
  { path: '/dsh-tasks', name: 'dsh-tasks' },
  { path: '/lanhu-evidence', name: 'lanhu-evidence' },
  { path: '/release-bundles', name: 'release-bundles' },
  { path: '/knowledge', name: 'knowledge' },
  { path: '/operations-release', name: 'operations-release' },
  { path: '/theme-lab', name: 'theme-lab' },
];

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: STATE, viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  const results = {};

  for (const r of ROUTES) {
    const rec = { url: r.path, status: 'ok', apiCalls: [], consoleErrors: [], pageErrors: [], loadMs: 0, redirect: '' };
    const apiMap = new Map(); // url -> {method, count, statuses:[]}
    const consoleErrs = [];
    const pageErrs = [];
    const respHandler = (resp) => {
      const u = resp.url();
      if (!u.includes('/api/')) return;
      const key = resp.request().method() + ' ' + u.split(BASE)[1] || u;
      if (!apiMap.has(key)) apiMap.set(key, { method: resp.request().method(), url: u.replace(BASE, ''), count: 0, statuses: [] });
      const e = apiMap.get(key);
      e.count++;
      e.statuses.push(resp.status());
    };
    const consoleHandler = m => { if (m.type() === 'error') consoleErrs.push(m.text().slice(0, 300)); };
    const pageErrHandler = e => pageErrs.push(String(e).slice(0, 400));
    page.on('response', respHandler);
    page.on('console', consoleHandler);
    page.on('pageerror', pageErrHandler);

    const t0 = Date.now();
    try {
      const resp = await page.goto(BASE + r.path, { waitUntil: 'networkidle', timeout: 45000 });
      await page.waitForTimeout(1500);
      rec.loadMs = Date.now() - t0;
      if (resp) rec.redirect = page.url();
      // 错误态检测
      const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 4000));
      fs.writeFileSync(`${SHOTS}${r.name}.txt`, bodyText);
      await page.screenshot({ path: `${SHOTS}${r.name}.png`, fullPage: false });
      rec.apiCalls = Array.from(apiMap.values()).sort((a, b) => b.count - a.count);
      rec.consoleErrors = consoleErrs;
      rec.pageErrors = pageErrs;
      rec.duplicated = rec.apiCalls.filter(c => c.count > 1).length;
      rec.totalApi = rec.apiCalls.reduce((s, c) => s + c.count, 0);
    } catch (e) {
      rec.status = 'error: ' + e.message.slice(0, 200);
      await page.screenshot({ path: `${SHOTS}${r.name}-error.png` }).catch(() => {});
    }
    page.off('response', respHandler);
    page.off('console', consoleHandler);
    page.off('pageerror', pageErrHandler);
    results[r.path] = rec;
    console.log(`${r.name}: ${rec.status} api=${rec.totalApi} dup=${rec.duplicated} err=${rec.consoleErrors.length + rec.pageErrors.length} ${rec.loadMs}ms`);
  }
  fs.writeFileSync(EVID + '03-all-pages.json', JSON.stringify(results, null, 2));
  // 汇总报告
  const summary = Object.values(results).map(v => ({
    page: v.url, status: v.status, totalApi: v.totalApi, dup: v.duplicated,
    consoleErrors: v.consoleErrors.length, pageErrors: v.pageErrors.length, loadMs: v.loadMs,
  }));
  fs.writeFileSync(EVID + '03-summary.json', JSON.stringify(summary, null, 2));
  console.log('DONE. summary saved.');
  await browser.close();
})();
