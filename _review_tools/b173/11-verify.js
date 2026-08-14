// B173-11: 追查 ①用例保存后是否真的入库 ②计划保存失败原因
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
  const apiLog = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('/api/')) apiLog.push({ m: resp.request().method(), u: decodeURIComponent(u.replace(BASE, '').split('?')[0]), s: resp.status(), t: Date.now() });
  });
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE ERR:', m.text().slice(0, 300)); });
  const note = (m) => console.log('###', m);

  // ===== 1) 用例创建 + 立即搜索验证 =====
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建用例/ }).first().click();
  await page.waitForTimeout(1200);
  const title = `${PREFIX}验证入库-${Date.now() % 1000000}`;
  await page.locator('[role="dialog"] input[name="title"]').fill(title);
  await page.locator('[role="dialog"] textarea[name="preconditions"]').fill('B173 前置条件');
  await page.locator('[role="dialog"] textarea[name="expected_result"]').fill('B173 预期结果');
  const areas = page.locator('[role="dialog"] textarea');
  const n = await areas.count();
  for (let i = 0; i < n; i++) {
    const ph = await areas.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('步骤')) { await areas.nth(i).fill('1. 打开页面'); break; }
  }
  // 域
  await page.locator('[role="dialog"] [role="combobox"]').filter({ hasText: '选择域' }).click();
  await page.waitForTimeout(600);
  const opt = page.locator('[role="option"]').filter({ hasText: /用户端$/ }).first();
  if (await opt.count()) await opt.click();
  await page.waitForTimeout(500);
  // 模块
  await page.locator('[role="dialog"] [role="combobox"]').filter({ hasText: '选择模块' }).click();
  await page.waitForTimeout(600);
  const modOpt = page.locator('[role="option"]').first();
  if (await modOpt.count()) await modOpt.click();
  await page.waitForTimeout(400);
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(3500);
  const post = apiLog.filter(r => r.m === 'POST' && r.u.includes('test-cases'));
  note('创建 POST 请求: ' + JSON.stringify(post.slice(-3)));
  note('保存后 dialog=' + (await page.locator('[role="dialog"]').count()));
  // 搜索验证
  const sb = page.locator('input[placeholder="搜索标题/关键字"]').first();
  await sb.fill(title);
  await page.locator('button').filter({ hasText: /^搜索$/ }).first().click();
  await page.waitForTimeout(2500);
  const rows = await page.locator('tbody tr').count();
  note(`搜索'${title}' 结果行=${rows}`);
  if (rows > 0) {
    note('第一行: ' + (await page.locator('tbody tr').first().innerText()).replace(/\n/g, ' | ').slice(0, 250));
  }
  // 清理：删除该用例
  if (rows > 0) {
    const row = page.locator('tbody tr').first();
    const delBtn = row.getByRole('button', { name: /删除/ });
    note('行操作按钮: ' + JSON.stringify(await row.locator('button').allInnerTexts()));
    if (await delBtn.count()) {
      await delBtn.first().click();
      await page.waitForTimeout(600);
      const confirms = page.locator('[role="dialog"] button, [role="alertdialog"] button');
      const txts = await confirms.allInnerTexts();
      note('确认按钮: ' + JSON.stringify(txts));
      await page.locator('[role="dialog"] button').filter({ hasText: /删除|确认|确定/ }).last().click().catch(() => {});
      await page.waitForTimeout(2000);
      const delPost = apiLog.filter(r => r.m === 'DELETE' && r.u.includes('test-cases'));
      note('DELETE 请求: ' + JSON.stringify(delPost.slice(-2)));
      note('删除后 dialog=' + (await page.locator('[role="dialog"]').count()));
    }
  }

  // ===== 2) 计划创建失败原因 =====
  await page.goto(BASE + '/testplan', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建计划/ }).first().click();
  await page.waitForTimeout(1000);
  // 不填直接保存看校验
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(1200);
  const errs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="dialog"] [role="alert"], [role="dialog"] .text-destructive')).map(e => e.innerText.trim().slice(0, 100)));
  note('计划空表单保存错误提示: ' + JSON.stringify(errs));
  // 填名称再保存
  const planTitle = `${PREFIX}计划-${Date.now() % 1000000}`;
  const pInputs = page.locator('[role="dialog"] input');
  const pn = await pInputs.count();
  for (let i = 0; i < pn; i++) {
    const ph = await pInputs.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('名称')) { await pInputs.nth(i).fill(planTitle); note('填名称成功: ' + ph); }
    if (String(ph).includes('编号')) { await pInputs.nth(i).fill('B173-' + (Date.now() % 1000000)); note('填编号成功: ' + ph); }
  }
  await page.screenshot({ path: EVID + '11-plan-filled.png' }).catch(() => {});
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(3000);
  note('填名称后保存 dialog=' + (await page.locator('[role="dialog"]').count()));
  const post2 = apiLog.filter(r => r.m === 'POST' && (r.u.includes('test-plans') || r.u.includes('plans')));
  note('计划 POST: ' + JSON.stringify(post2.slice(-3)));
  // 若保存成功，记录计划ID并删除
  const delPlans = apiLog.filter(r => r.m === 'DELETE' && r.u.includes('plan'));
  note('计划 DELETE: ' + JSON.stringify(delPlans.slice(-2)));

  fs.writeFileSync(EVID + '11-verify-log.json', JSON.stringify({ apiLog }, null, 2));
  await browser.close();
})();
