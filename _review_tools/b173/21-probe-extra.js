// B173-21: 补充探测 — 角色管理/邀请码内容、Agent执行对话框、UI新建任务、知识中心子tab
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
  const note = (m) => console.log('###', m);

  // 角色管理（等待更久）
  await page.goto(BASE + '/system', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  await page.getByRole('tab', { name: '角色管理' }).first().click();
  await page.waitForTimeout(2500);
  const roleText = await page.evaluate(() => document.body.innerText.slice(400, 2500));
  fs.writeFileSync(EVID + '21-roles.txt', roleText);
  note('角色管理: ' + roleText.replace(/\n/g, ' | ').slice(0, 400));

  await page.getByRole('tab', { name: '邀请码' }).first().click();
  await page.waitForTimeout(2500);
  const inviteText = await page.evaluate(() => document.body.innerText.slice(400, 2000));
  fs.writeFileSync(EVID + '21-invite.txt', inviteText);
  note('邀请码: ' + inviteText.replace(/\n/g, ' | ').slice(0, 300));

  // Agent 执行对话框
  await page.goto(BASE + '/agent-workbench', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  const execBtns = page.getByRole('button', { name: /^执行$/ });
  note('Agent 执行按钮数: ' + (await execBtns.count()));
  if (await execBtns.count()) {
    await execBtns.first().click();
    await page.waitForTimeout(2000);
    const dlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 800) : 'NO'; });
    fs.writeFileSync(EVID + '21-agent-dialog.txt', dlg);
    note('Agent 执行对话框: ' + dlg.replace(/\n/g, ' | ').slice(0, 400));
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(500);
  }

  // UI 新建任务（切到任务tab后再点）
  await page.goto(BASE + '/uitest', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  await page.getByRole('tab', { name: /任务/ }).first().click().catch(() => {});
  await page.waitForTimeout(1500);
  const newTask = page.getByRole('button', { name: /新建任务/ });
  note('新建任务按钮数: ' + (await newTask.count()));
  if (await newTask.count()) {
    await newTask.first().click();
    await page.waitForTimeout(2000);
    const dlg = await page.evaluate(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.innerText.slice(0, 1000) : 'NO'; });
    fs.writeFileSync(EVID + '21-uitask-dialog.txt', dlg);
    note('UI 新建任务对话框: ' + dlg.replace(/\n/g, ' | ').slice(0, 500));
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(500);
  }

  // 知识中心：项目知识 tab
  await page.goto(BASE + '/knowledge', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.getByRole('tab', { name: '项目知识' }).first().click();
  await page.waitForTimeout(2000);
  const kText = await page.evaluate(() => document.body.innerText.slice(400, 2000));
  fs.writeFileSync(EVID + '21-knowledge-project.txt', kText);
  note('知识中心-项目知识: ' + kText.replace(/\n/g, ' | ').slice(0, 400));

  await browser.close();
})();
