// B173-18: 追查 ①环境创建失败 ②缺陷是否有删除入口
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
  page.on('requestfailed', r => console.log('REQ FAILED:', r.url().slice(0, 150), r.failure()?.errorText));
  const note = (m) => console.log('###', m);

  // ===== 1) 环境创建 =====
  await page.goto(BASE + '/environment', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /新建环境/ }).first().click();
  await page.waitForTimeout(1000);
  const envName = 'B173TMP-环境-' + (Date.now() % 100000);
  const input = page.locator('[role="dialog"] input').first();
  await input.fill(envName);
  note('环境名已填: ' + envName + ' value=' + (await input.inputValue()));
  // 类型默认 test，Base URL 填一下
  const baseUrlInput = page.locator('[role="dialog"] input').nth(1);
  if (await baseUrlInput.count()) await baseUrlInput.fill('https://example.com');
  await page.screenshot({ path: EVID + '18-env-filled.png' }).catch(() => {});
  await page.locator('[role="dialog"] button').filter({ hasText: /^创建$/ }).first().click();
  await page.waitForTimeout(3000);
  const post = apiLog.filter(r => r.m === 'POST' && r.u.includes('environments'));
  note('POST environments: ' + JSON.stringify(post.slice(-2)));
  note('dialog=' + (await page.locator('[role="dialog"]').count()));
  const errs = await page.evaluate(() => Array.from(document.querySelectorAll('[role="alert"]')).map(e => e.innerText.trim().slice(0, 150)));
  note('错误提示: ' + JSON.stringify(errs));
  // 若创建成功，立即删除
  if (post.length) {
    await page.waitForTimeout(1000);
    // 查找刚创建的环境行
    const row = page.locator('tbody tr').filter({ hasText: envName });
    if (await row.count()) {
      const btnAria = await row.evaluate(el => Array.from(el.querySelectorAll('button')).map(b => b.getAttribute('aria-label') || (b.innerText || '').trim()));
      note('环境行按钮: ' + JSON.stringify(btnAria));
      const del = row.locator('[aria-label*="删除"]');
      if (await del.count()) {
        await del.first().click();
        await page.waitForTimeout(600);
        const confirm = page.locator('[role="alertdialog"] button').filter({ hasText: /^删除$/ });
        if (await confirm.count()) { await confirm.first().click(); await page.waitForTimeout(2000); }
        note('环境删除 DELETE: ' + JSON.stringify(apiLog.filter(r => r.m === 'DELETE' && r.u.includes('environments'))));
      }
    }
  }

  // ===== 2) 缺陷删除入口 =====
  await page.goto(BASE + '/defect', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  const row = page.locator('tbody tr').filter({ hasText: 'B173TMP' }).first();
  if (await row.count()) {
    const btnAria = await row.evaluate(el => Array.from(el.querySelectorAll('button')).map(b => b.getAttribute('aria-label') || (b.innerText || '').trim()));
    note('缺陷行按钮: ' + JSON.stringify(btnAria));
    // 点击编辑看是否可删除
    const edit = row.locator('button').filter({ hasText: /编辑/ });
    if (await edit.count()) {
      await edit.first().click();
      await page.waitForTimeout(1500);
      const dlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 800) : 'NO'; });
      fs.writeFileSync(EVID + '18-defect-edit-dialog.txt', dlg);
      note('编辑对话框: ' + dlg.replace(/\n/g, ' | ').slice(0, 400));
      const btns = await page.evaluate(() => Array.from(document.querySelectorAll('[role="dialog"] button')).map(b => (b.innerText || '').trim().slice(0, 20)).filter(Boolean));
      note('编辑对话框按钮: ' + JSON.stringify(btns));
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }
    // 检查 API 是否有删除能力（通过 openapi）
    const delApi = await page.request.get(BASE + '/api/v1/defects/' + '', { headers: { 'X-Project-Id': '1' } }).catch(() => null);
  } else {
    note('B173TMP 缺陷不存在（可能已被自动清理）');
  }

  // 检查缺陷删除接口定义（通过 OPTIONS 或直接尝试）
  const resp = await page.request.get('https://test-platform.up.railway.app/openapi.json').catch(e => null);
  if (resp && resp.ok()) {
    const spec = await resp.json();
    const paths = Object.keys(spec.paths).filter(p => p.includes('/defects'));
    note('defects 相关端点: ' + JSON.stringify(paths));
    const delPath = paths.find(p => p.includes('{defect_id}'));
    if (delPath) {
      const methods = Object.keys(spec.paths[delPath]);
      note(delPath + ' 方法: ' + JSON.stringify(methods));
    }
  } else {
    note('openapi 获取失败: ' + (resp ? resp.status() : 'null'));
  }

  fs.writeFileSync(EVID + '18-trace2-log.json', JSON.stringify(apiLog, null, 2));
  await browser.close();
})();
