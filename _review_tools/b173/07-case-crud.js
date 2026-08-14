// B173-07: 深度交互测试 v3 — 用例服务完整 CRUD（新建→搜索→编辑→删除）+ 请求日志
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
    if (u.includes('/api/')) apiLog.push({ m: resp.request().method(), u: u.replace(BASE, '').split('?')[0], s: resp.status(), t: Date.now() });
  });
  const note = (msg) => { console.log('###', msg); log.push({ t: 'note', text: msg }); };
  const countGet = (sub) => apiLog.filter(r => r.m === 'GET' && r.u.includes(sub)).length;

  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // ===== 1) 搜索防抖量化 =====
  const before = countGet('test-cases');
  const searchBox = page.locator('input[placeholder="搜索标题/关键字"]').first();
  await searchBox.pressSequentially('UGC', { delay: 300 });
  await page.waitForTimeout(1800);
  const after = countGet('test-cases');
  note(`逐字输入UGC: 增量请求 ${after - before} 次（防抖应=1）`);
  await searchBox.fill('');
  await page.waitForTimeout(1000);

  // ===== 2) 新建用例 =====
  await page.getByRole('button', { name: /新建用例/ }).first().click();
  await page.waitForTimeout(1200);
  const title = `${PREFIX}交互审查用例-${Date.now() % 1000000}`;
  await page.locator('[role="dialog"] input[name="title"]').fill(title);
  await page.locator('[role="dialog"] textarea[name="preconditions"]').fill('B173 深度审查前置条件-验证保存');
  await page.locator('[role="dialog"] textarea[name="expected_result"]').fill('B173 深度审查预期结果-验证保存');
  // 步骤：找 placeholder 含"步骤"的 textarea
  const stepArea = page.locator('[role="dialog"] textarea').filter({ has: undefined });
  const areas = page.locator('[role="dialog"] textarea');
  const n = await areas.count();
  for (let i = 0; i < n; i++) {
    const ph = await areas.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('步骤')) { await areas.nth(i).fill('1. 打开页面'); break; }
  }
  // 选择所属模块（必填）— 探测下拉
  const moduleBtn = page.locator('[role="dialog"] button').filter({ hasText: /选择模块/ }).first();
  if (await moduleBtn.count()) {
    await moduleBtn.click();
    await page.waitForTimeout(800);
    // 从弹出列表中选第一项
    const item = page.locator('[role="option"], [role="menuitem"], [data-radix-collection-item]').first();
    if (await item.count()) {
      const txt = (await item.innerText()).trim().slice(0, 30);
      await item.click().catch(async () => {
        // 备选：点击列表中的文本
        await page.locator('div[role="listbox"] div, [data-slot="select-content"] div').filter({ hasText: /用户端/ }).first().click().catch(() => {});
      });
      note('module selected: ' + txt);
    } else {
      note('module dropdown options NOT found');
    }
    await page.waitForTimeout(500);
  } else {
    note('module select button NOT found (可能非必填)');
  }
  await page.screenshot({ path: EVID + '07-case-dialog-filled.png' }).catch(() => {});
  await page.getByRole('button', { name: '保存' }).first().click();
  await page.waitForTimeout(3000);
  const dlgCount = await page.locator('[role="dialog"]').count();
  note(`保存后 dialog=${dlgCount}（0=关闭成功）`);

  // ===== 3) 搜索刚创建的用例 =====
  await page.locator('input[placeholder="搜索标题/关键字"]').first().fill(title);
  await page.waitForTimeout(2000);
  const rows = page.locator('tbody tr');
  const rowCount = await rows.count();
  note(`搜索'${title}' 结果行数=${rowCount}`);
  let foundTitle = '';
  if (rowCount > 0) {
    foundTitle = (await rows.first().innerText()).slice(0, 200);
    note('第一行内容: ' + foundTitle.replace(/\n/g, ' | '));
  }

  // ===== 4) 编辑用例 =====
  if (rowCount > 0) {
    const editBtn = rows.first().getByRole('button', { name: /编辑/ });
    if (await editBtn.count()) {
      await editBtn.first().click();
      await page.waitForTimeout(1200);
      await page.locator('[role="dialog"] textarea[name="preconditions"]').fill('B173 深度审查-已编辑前置条件');
      await page.getByRole('button', { name: '保存' }).first().click();
      await page.waitForTimeout(2500);
      note('编辑保存完成, dialog=' + (await page.locator('[role="dialog"]').count()));
    } else {
      note('编辑按钮不存在');
    }
  }

  // ===== 5) 删除用例 =====
  if (rowCount > 0) {
    const row = page.locator('tbody tr').filter({ hasText: title }).first();
    const delBtn = row.getByRole('button', { name: /删除/ });
    if (await delBtn.count()) {
      await delBtn.first().click();
      await page.waitForTimeout(800);
      const confirm = page.getByRole('button', { name: /确认|确定|删除/ }).last();
      await confirm.click().catch(() => note('删除确认按钮点击失败'));
      await page.waitForTimeout(2000);
      const afterDel = await page.locator('tbody tr').count();
      note(`删除后剩余行=${afterDel}`);
    } else {
      note('删除按钮不存在（行操作：' + JSON.stringify(await row.locator('button').allInnerTexts()) + '）');
    }
  }

  fs.writeFileSync(EVID + '07-case-crud-log.json', JSON.stringify({ log, apiLog }, null, 2));
  console.log('TOTAL API:', apiLog.length);
  const dup = {};
  apiLog.filter(r => r.m === 'GET').forEach(r => { const k = r.m + r.u; dup[k] = (dup[k] || 0) + 1; });
  console.log('DUP GETs:', JSON.stringify(Object.entries(dup).filter(([, c]) => c > 1)));
  await browser.close();
})();
