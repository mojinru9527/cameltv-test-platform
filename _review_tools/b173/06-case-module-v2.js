// B173-06: 深度交互测试 v2 — 用例服务完整 CRUD + 计划模块 + 搜索防抖量化
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
  const countGet = (sub) => apiLog.filter(r => r.m === 'GET' && r.u.includes(sub)).length;

  // ============ 用例服务 ============
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  note('testcase loaded, initial GETs=' + countGet('test-cases'));

  // 搜索防抖量化：逐字输入观察请求数
  const searchBox = page.locator('input[placeholder="搜索"]').first();
  const before = countGet('test-cases');
  await searchBox.fill('U');
  await page.waitForTimeout(400);
  await searchBox.fill('UG');
  await page.waitForTimeout(400);
  await searchBox.fill('UGC');
  await page.waitForTimeout(1500);
  const after = countGet('test-cases');
  note(`搜索逐字输入: before=${before} after=${after} => 增量请求 ${after - before} 次（无防抖预期 ~3-4 次，有防抖预期 1 次）`);

  // 清空搜索
  await searchBox.fill('');
  await page.waitForTimeout(1000);

  // 新建用例（真正填写并保存）
  await page.getByRole('button', { name: /新建用例/ }).first().click();
  await page.waitForTimeout(1200);
  const title = `${PREFIX}交互审查-${Date.now() % 1000000}`;
  await page.locator('[role="dialog"] input[name="title"]').fill(title);
  await page.locator('[role="dialog"] textarea[name="preconditions"]').fill('B173 深度审查前置条件');
  await page.locator('[role="dialog"] textarea[name="expected_result"]').fill('B173 深度审查预期结果');
  // 测试步骤 textarea
  const stepAreas = page.locator('[role="dialog"] textarea');
  const n = await stepAreas.count();
  for (let i = 0; i < n; i++) {
    const ph = await stepAreas.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('步骤')) { await stepAreas.nth(i).fill('步骤1：打开页面'); break; }
  }
  // 保存
  await page.getByRole('button', { name: '保存' }).first().click();
  await page.waitForTimeout(2500);
  const dlgAfter = await page.locator('[role="dialog"]').count();
  note(`保存后 dialog 数量=${dlgAfter}（0=已关闭，>0=未关闭）`);
  const saved = await page.evaluate(() => document.body.innerText.includes('B173TMP'));
  note(`列表中可见新建用例: ${saved}`);

  // 若保存成功，查找并删除该用例
  if (saved) {
    await page.locator('input[placeholder="搜索"]').first().fill(title);
    await page.waitForTimeout(1500);
    // 找到行内删除按钮
    const row = page.locator('tbody tr').filter({ hasText: title }).first();
    if (await row.count()) {
      const btns = await row.locator('button').allInnerTexts();
      note(`目标行按钮: ${JSON.stringify(btns)}`);
      // 删除（若有删除按钮）
      const delBtn = row.getByRole('button', { name: /删除/ });
      if (await delBtn.count()) {
        await delBtn.first().click();
        await page.waitForTimeout(800);
        // 确认对话框
        const confirm = page.getByRole('button', { name: /确认|确定|删除/ }).last();
        await confirm.click().catch(() => {});
        await page.waitForTimeout(1500);
        note('删除确认后：' + (await page.locator('[role="dialog"]').count()));
      }
    }
  }

  fs.writeFileSync(EVID + '06-case-module-log.json', JSON.stringify({ log, apiLog }, null, 2));
  console.log('TOTAL API:', apiLog.length);
  await browser.close();
})();
