// B173-35: 响应式检查 — 375/768/1280/1600 视口下关键页面溢出与布局
const fs = require('fs');
const { chromium } = require('playwright');
const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';
const EVID = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';

const PAGES = ['/workbench', '/testcase', '/testplan', '/defect', '/requirement', '/knowledge'];

(async () => {
  fs.mkdirSync(EVID, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const results = {};
  for (const vp of [{ w: 375, h: 812, name: 'mobile' }, { w: 768, h: 1024, name: 'tablet' }, { w: 1280, h: 800, name: 'desktop' }]) {
    const context = await browser.newContext({ storageState: STATE, viewport: { width: vp.w, height: vp.h } });
    const page = await context.newPage();
    for (const p of PAGES) {
      try {
        await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
        await page.waitForTimeout(1200);
        const m = await page.evaluate(() => ({
          overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
          sw: document.documentElement.scrollWidth,
          iw: window.innerWidth,
          sidebar: !!document.querySelector('[data-slot="sidebar"]'),
        }));
        if (!results[p]) results[p] = {};
        results[p][vp.name] = m;
        console.log(`${vp.name} ${p}: overflowX=${m.overflowX} (${m.sw}/${m.iw})`);
      } catch (e) {
        console.log(`${vp.name} ${p}: ERR ${e.message.slice(0, 80)}`);
      }
    }
    await context.close();
  }
  fs.writeFileSync(EVID + '35-responsive.json', JSON.stringify(results, null, 2));
  await browser.close();
})();
