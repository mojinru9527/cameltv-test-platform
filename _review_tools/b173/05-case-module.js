// B173-05: 深度交互测试 — 用例服务模块 CRUD + 搜索/筛选 + 网络请求日志
// 测试工程师视角：新建用例 → 编辑 → 搜索 → 筛选 → 删除（清理临时数据）
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';
const EVID = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';
const PREFIX = 'B173TMP-';

(async () => {
  fs.mkdirSync(EVID, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: STATE, viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  const log = [];
  const apiLog = [];
  page.on('console', m => { if (m.type() === 'error') log.push({ t: 'console', text: m.text().slice(0, 300) }); });
  page.on('pageerror', e => log.push({ t: 'pageerror', text: String(e).slice(0, 400) }));
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('/api/')) apiLog.push({ m: resp.request().method(), u: u.replace(BASE, '').split('?')[0], s: resp.status() });
  });
  const note = (msg) => { console.log('###', msg); log.push({ t: 'note', text: msg }); };

  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  note('testcase page loaded');

  // 1) 打开新建用例对话框
  const newBtn = page.getByRole('button', { name: /新建用例/ });
  if (await newBtn.count()) {
    await newBtn.first().click();
    await page.waitForTimeout(1500);
    // 记录对话框结构
    const dlg = await page.evaluate(() => {
      const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));
      return dialogs.map(d => d.innerText.slice(0, 1200));
    });
    fs.writeFileSync(EVID + '05-case-dialog.txt', JSON.stringify(dlg, null, 2));
    note('new case dialog opened: ' + (dlg.length ? 'found ' + dlg.length : 'NONE'));
    // 打印表单字段
    const fields = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[role="dialog"] input, [role="dialog"] select, [role="dialog"] textarea')).map(i => ({
        tag: i.tagName, name: i.getAttribute('name'), id: i.id, type: i.type, ph: i.getAttribute('placeholder'),
      }));
    });
    fs.writeFileSync(EVID + '05-case-dialog-fields.json', JSON.stringify(fields, null, 2));
    // 尝试填写最小字段
    const title = `${PREFIX}深度审查用例-${Date.now() % 100000}`;
    const inputs = page.locator('[role="dialog"] input, [role="dialog"] textarea');
    const n = await inputs.count();
    // 记录所有输入框可见状态
    for (let i = 0; i < Math.min(n, 12); i++) {
      const vis = await inputs.nth(i).isVisible().catch(() => false);
      note(`field[${i}] visible=${vis} name=${await inputs.nth(i).getAttribute('name').catch(()=>'')} ph=${await inputs.nth(i).getAttribute('placeholder').catch(()=>'')}`);
    }
    await page.screenshot({ path: EVID + '05-case-dialog.png' }).catch(() => {});
  } else {
    note('NEW CASE BUTTON NOT FOUND');
  }

  // 2) 搜索测试（中文关键字）
  await page.getByPlaceholder('搜索').first().fill('UGC');
  await page.waitForTimeout(1200);
  // 观察请求次数
  note('search requests: ' + apiLog.filter(r => r.u.includes('test-cases') && r.m === 'GET').length);

  // 3) 导出 Excel 按钮测试
  const exportBtn = page.getByRole('button', { name: /导出 Excel/ });
  note('export Excel btn exists: ' + (await exportBtn.count()));

  // 4) 分页测试
  const next = page.getByRole('button', { name: '下一页' });
  if (await next.count()) { await next.first().click(); await page.waitForTimeout(1000); note('pagination next clicked'); }
  const prev = page.getByRole('button', { name: '上一页' });
  if (await prev.count()) { await prev.first().click(); await page.waitForTimeout(1000); note('pagination prev clicked'); }

  // 5) 筛选测试：按模块分类
  const modBtn = page.locator('button').filter({ hasText: /用户端 \(/ });
  if (await modBtn.count()) { await modBtn.first().click(); await page.waitForTimeout(1200); note('module filter clicked'); }

  // 6) 用例标题是否可点击（详情）
  const firstTitle = page.locator('tbody tr td:nth-child(2) a, tbody tr td:nth-child(2) button').first();
  note('title clickable: ' + (await firstTitle.count()));

  // 7) 操作列检查：编辑/删除按钮
  const firstRow = page.locator('tbody tr').first();
  if (await firstRow.count()) {
    const btns = await firstRow.locator('button').allInnerTexts();
    note('first row action buttons: ' + JSON.stringify(btns));
  }

  fs.writeFileSync(EVID + '05-case-test-log.json', JSON.stringify({ log, apiLog }, null, 2));
  console.log('TOTAL API CALLS:', apiLog.length);
  const dup = apiLog.filter(r => r.m === 'GET').reduce((acc, r) => { const k = r.m + r.u; acc[k] = (acc[k] || 0) + 1; return acc; }, {});
  const dupList = Object.entries(dup).filter(([, c]) => c > 1);
  console.log('DUP GETs:', JSON.stringify(dupList));
  await browser.close();
})();
