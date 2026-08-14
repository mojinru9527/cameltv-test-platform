// B173-10: 完整用例创建（选域+模块）→ 计划模块深测 → 报告/缺陷模块
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
  page.on('console', m => { if (m.type() === 'error') log.push({ t: 'console', text: m.text().slice(0, 300) }); });
  page.on('pageerror', e => log.push({ t: 'pageerror', text: String(e).slice(0, 400) }));
  const note = (msg) => { console.log('###', msg); log.push({ t: 'note', text: msg }); };

  // ===== 用例创建完整流程 =====
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建用例/ }).first().click();
  await page.waitForTimeout(1200);
  const title = `${PREFIX}完整创建-${Date.now() % 1000000}`;
  await page.locator('[role="dialog"] input[name="title"]').fill(title);
  await page.locator('[role="dialog"] textarea[name="preconditions"]').fill('B173 前置条件');
  await page.locator('[role="dialog"] textarea[name="expected_result"]').fill('B173 预期结果');
  const areas = page.locator('[role="dialog"] textarea');
  const n = await areas.count();
  for (let i = 0; i < n; i++) {
    const ph = await areas.nth(i).getAttribute('placeholder').catch(() => '');
    if (String(ph).includes('步骤')) { await areas.nth(i).fill('1. 打开页面\n2. 点击按钮'); break; }
  }
  // 选择域
  await page.locator('[role="dialog"] [role="combobox"]').filter({ hasText: '选择域' }).click().catch(async () => {
    await page.locator('[role="dialog"] button').filter({ hasText: '选择域' }).first().click();
  });
  await page.waitForTimeout(800);
  // 选择第一个域选项（用户端）
  const opt = page.locator('[role="option"]').filter({ hasText: /用户端$/ }).first();
  if (await opt.count()) { await opt.click(); note('域=用户端 选中'); }
  else {
    const anyOpt = page.locator('[role="option"]').first();
    if (await anyOpt.count()) { note('首个域选项: ' + (await anyOpt.innerText()).trim()); await anyOpt.click(); }
    else note('域下拉无选项!');
  }
  await page.waitForTimeout(600);
  // 选择模块（依赖域）
  await page.locator('[role="dialog"] [role="combobox"]').filter({ hasText: '选择模块' }).click().catch(async () => {
    await page.locator('[role="dialog"] button').filter({ hasText: '选择模块' }).first().click();
  });
  await page.waitForTimeout(800);
  const modOpt = page.locator('[role="option"]').first();
  if (await modOpt.count()) { note('模块选项: ' + (await modOpt.innerText()).trim().slice(0, 40)); await modOpt.click(); }
  else note('模块下拉无选项!');
  await page.waitForTimeout(500);
  await page.screenshot({ path: EVID + '10-case-filled.png' }).catch(() => {});
  await page.locator('[role="dialog"] button').filter({ hasText: '保存' }).first().click();
  await page.waitForTimeout(3000);
  note('保存后 dialog=' + (await page.locator('[role="dialog"]').count()) + ' 页面含新用例=' + (await page.evaluate((t) => document.body.innerText.includes(t), title)));

  // ===== 测试计划模块 =====
  await page.goto(BASE + '/testplan', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  note('testplan loaded');
  await page.getByRole('button', { name: /新建计划/ }).first().click();
  await page.waitForTimeout(1200);
  // 探测新建计划对话框
  const planDlg = await page.evaluate(() => {
    const d = document.querySelector('[role="dialog"]');
    return d ? d.innerText.slice(0, 1000) : 'NO DIALOG';
  });
  fs.writeFileSync(EVID + '10-plan-dialog.txt', planDlg);
  note('计划对话框内容: ' + planDlg.replace(/\n/g, ' | ').slice(0, 300));
  // 填写并保存
  const planTitle = `${PREFIX}深度审查计划-${Date.now() % 1000000}`;
  const pInputs = page.locator('[role="dialog"] input');
  const pn = await pInputs.count();
  for (let i = 0; i < Math.min(pn, 5); i++) {
    const ph = await pInputs.nth(i).getAttribute('placeholder').catch(() => '');
    if (ph && ph.includes('名称')) { await pInputs.nth(i).fill(planTitle); note('计划名填入: ' + ph); }
  }
  await page.screenshot({ path: EVID + '10-plan-dialog.png' }).catch(() => {});
  await page.locator('[role="dialog"] button').filter({ hasText: /保存|创建|确定/ }).first().click().catch(() => note('计划保存按钮点击失败'));
  await page.waitForTimeout(2500);
  note('计划保存后 dialog=' + (await page.locator('[role="dialog"]').count()));

  fs.writeFileSync(EVID + '10-crud-log.json', JSON.stringify(log, null, 2));
  await browser.close();
})();
