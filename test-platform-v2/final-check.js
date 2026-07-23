// Final targetted check - wait specifically for batch-34 elements with console log capture
const { chromium } = require('playwright');
const path = require('path');

const SS = 'C:/Users/26029/.claude/skills/playwright-skill/screenshots';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 80 });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  // Capture ALL console messages
  const consoleMsgs = [];
  page.on('console', (msg) => consoleMsgs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', (err) => consoleMsgs.push(`[PAGE_ERR] ${err.message}`));

  // Login
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 5000 });
  await page.waitForTimeout(2000);

  // Go to requirements with a full hard refresh
  await page.goto('http://localhost:5173/requirement', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(3000);

  // Dump console errors
  const errors = consoleMsgs.filter((m) => m.includes('error') || m.includes('ERR') || m.includes('warn'));
  console.log('Console errors/warnings:');
  errors.forEach((e) => console.log('  ', e));

  // Try to wait for the lanhu settings button
  let lanhuFound = false;
  try {
    await page.waitForSelector('button:has-text("蓝湖设置")', { timeout: 3000 });
    console.log('\n*** "蓝湖设置" button FOUND via waitForSelector! ***');
    lanhuFound = true;
  } catch {
    console.log('\n*** "蓝湖设置" button NOT found via waitForSelector ***');
  }

  // Check full page body text
  const bodyText = await page.innerText('body');
  console.log('Body includes "蓝湖设置":', bodyText.includes('蓝湖设置'));
  console.log('Body includes "Settings":', bodyText.includes('Settings'));
  console.log('Body includes "蓝湖项目配置":', bodyText.includes('蓝湖项目配置'));

  // Take full-page screenshot
  await page.screenshot({ path: path.join(SS, 'batch34-final-req-fullpage.png'), fullPage: true });
  console.log('Full-page screenshot saved.');

  // Now test testcase page
  await page.goto('http://localhost:5173/testcase', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  let reviewFound = false;
  try {
    await page.waitForSelector('button[title="提交评审"]', { timeout: 3000 });
    console.log('\n*** "提交评审" button FOUND! ***');
    reviewFound = true;
  } catch {
    console.log('\n*** "提交评审" button NOT found ***');
  }

  const tcBody = await page.innerText('body');
  console.log('Testcase body includes "提交评审":', tcBody.includes('提交评审'));

  // Now test integration page
  await page.goto('http://localhost:5173/integration', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  let linkageFound = false;
  try {
    await page.waitForSelector('h2:has-text("模块联动追踪")', { timeout: 3000 });
    console.log('\n*** "模块联动追踪" heading FOUND! ***');
    linkageFound = true;
  } catch {
    console.log('\n*** "模块联动追踪" heading NOT found ***');
  }

  const intBody = await page.innerText('body');
  console.log('Integration body includes "模块联动追踪":', intBody.includes('模块联动追踪'));

  // Now test release bundles
  await page.goto('http://localhost:5173/release-bundles', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  console.log('\nRelease bundles URL:', page.url());

  // Find first bundle link and click
  const bundleLink = await page.$('table tbody tr a');
  if (bundleLink) {
    await bundleLink.click();
    await page.waitForTimeout(2000);
    console.log('Bundle detail URL:', page.url());
    const detailBody = await page.innerText('body');
    console.log('Has "回归范围":', detailBody.includes('回归范围'));
    console.log('Has "触发UI回归":', detailBody.includes('触发UI回归'));
  } else {
    console.log('No bundle links found in table');
    // Try clicking first row
    const firstRow = await page.$('table tbody tr');
    if (firstRow) {
      await firstRow.click();
      await page.waitForTimeout(2000);
      console.log('After row click URL:', page.url());
    }
  }

  await browser.close();
  console.log('\nDone.');
})();
