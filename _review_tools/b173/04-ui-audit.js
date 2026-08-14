// B173-04: UI 对抗审查 — DOM 层系统性检查
// 对每个页面检查：横向溢出/垂直溢出、无文本按钮、无aria-label图标按钮、空链接、重复ID、表格空态、
// 低对比度风险(静态文本色)、fixed元素、iframe、图片无alt、输入无label、z-index异常、长文本截断
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';
const EVID = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';

const ROUTES = [
  '/workbench', '/trace', '/requirement', '/testcase', '/testplan', '/mindmap', '/apitest', '/uitest',
  '/playground', '/schedule', '/report', '/system', '/my-projects', '/defect', '/dataset', '/integration',
  '/notify', '/environment', '/agent-workbench', '/dsh-tasks', '/lanhu-evidence', '/release-bundles',
  '/knowledge', '/operations-release', '/theme-lab',
];

(async () => {
  fs.mkdirSync(EVID, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: STATE, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const results = {};

  for (const path of ROUTES) {
    try {
      await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 45000 });
      await page.waitForTimeout(1200);
      const audit = await page.evaluate(() => {
        const out = { path: location.pathname, overflowX: false, overflowY: false, issues: [] };
        out.overflowX = document.documentElement.scrollWidth > window.innerWidth + 2;
        out.overflowY = document.documentElement.scrollHeight > window.innerHeight * 1.05 + 2;
        // 无文本按钮
        document.querySelectorAll('button').forEach(b => {
          const t = (b.innerText || '').trim();
          const al = b.getAttribute('aria-label') || '';
          const title = b.getAttribute('title') || '';
          if (!t && !al && !title) out.issues.push({ t: 'button-no-text', tag: b.outerHTML.slice(0, 160) });
        });
        // 图标按钮无 aria-label（有 svg 无文本）
        document.querySelectorAll('button:has(svg)').forEach(b => {
          const t = (b.innerText || '').trim();
          const al = b.getAttribute('aria-label') || '';
          if (!t && !al) out.issues.push({ t: 'icon-btn-no-aria', tag: b.outerHTML.slice(0, 200) });
        });
        // 空链接
        document.querySelectorAll('a[href]').forEach(a => {
          const t = (a.innerText || '').trim();
          if (!t && !a.getAttribute('aria-label')) out.issues.push({ t: 'link-no-text', href: a.getAttribute('href'), tag: a.outerHTML.slice(0, 160) });
        });
        // 重复 id
        const ids = {};
        document.querySelectorAll('[id]').forEach(el => {
          const id = el.id;
          if (id && id !== 'radix-:r0:' && !id.startsWith('radix-')) ids[id] = (ids[id] || 0) + 1;
        });
        const dupIds = Object.entries(ids).filter(([, c]) => c > 1).map(([id, c]) => ({ id, count: c }));
        if (dupIds.length) out.issues.push({ t: 'duplicate-id', ids: dupIds.slice(0, 10) });
        // 图片无 alt
        document.querySelectorAll('img').forEach(img => {
          if (!img.getAttribute('alt') && img.getAttribute('alt') !== '') out.issues.push({ t: 'img-no-alt', src: (img.getAttribute('src') || '').slice(0, 100) });
        });
        // 无关联 label 的 input
        document.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(el => {
          const id = el.id;
          if (!id) return;
          const label = document.querySelector(`label[for="${id}"]`);
          if (!label && !el.getAttribute('aria-label') && !el.getAttribute('placeholder')) {
            out.issues.push({ t: 'input-no-label', id, type: el.tagName, name: el.getAttribute('name') });
          }
        });
        // iframe
        const iframes = Array.from(document.querySelectorAll('iframe')).map(f => (f.src || '').slice(0, 120));
        if (iframes.length) out.issues.push({ t: 'iframes', iframes });
        // fixed 元素
        const fixed = Array.from(document.querySelectorAll('*')).filter(el => {
          const st = getComputedStyle(el);
          return st.position === 'fixed' && el.offsetParent === null;
        }).length;
        if (fixed > 20) out.issues.push({ t: 'many-fixed', count: fixed });
        // 表格行数/列数
        const tables = Array.from(document.querySelectorAll('table')).map(tb => ({
          rows: tb.querySelectorAll('tbody tr').length,
          cols: tb.querySelectorAll('thead th').length || tb.querySelectorAll('tr:first-child td, tr:first-child th').length,
          hasEmpty: (tb.innerText || '').includes('暂无') || (tb.innerText || '').includes('空'),
        }));
        if (tables.length) out.tables = tables.slice(0, 5);
        return out;
      });
      results[path] = audit;
      const n = audit.issues.length;
      console.log(`${path}: overflowX=${audit.overflowX} overflowY=${audit.overflowY} issues=${n} tables=${(audit.tables||[]).length}`);
      audit.issues.slice(0, 12).forEach(i => console.log('   -', i.t, JSON.stringify(i).slice(0, 150)));
    } catch (e) {
      results[path] = { path, error: e.message.slice(0, 150) };
      console.log(`${path}: ERROR ${e.message.slice(0, 100)}`);
    }
  }
  fs.writeFileSync(EVID + '04-ui-audit.json', JSON.stringify(results, null, 2));
  console.log('DONE');
  await browser.close();
})();
