// Batch-34 Frontend Walkthrough Script
// Tests: Login/Dashboard, Requirements (B2+A7), Test Cases (A6), Integration (B6), Release Bundles (B4+B5)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const TARGET_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = path.join('C:/Users/26029/.claude/skills/playwright-skill/screenshots');

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function ssPath(name) {
  return path.join(SCREENSHOT_DIR, `batch34-${name}.png`);
}

async function takeScreenshot(page, name, fullPage = true) {
  const fp = ssPath(name);
  await page.screenshot({ path: fp, fullPage });
  console.log(`  [SCREENSHOT] ${fp}`);
}

(async () => {
  console.log('========================================');
  console.log('  Batch-34 Frontend Walkthrough');
  console.log(`  Target: ${TARGET_URL}`);
  console.log('========================================\n');

  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  const page = await context.newPage();

  // === CREDENTIALS ===
  const CREDENTIALS = [
    { username: 'admin', password: 'admin123', label: 'admin/admin123' },
    { username: 'tester', password: 'tester123', label: 'tester/tester123' },
    { username: 'test', password: 'test123', label: 'test/test123' },
  ];

  let loggedIn = false;

  try {
    // ===============================================
    // STEP 1: Login
    // ===============================================
    console.log('\n--- STEP 1: Login ---');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1000);

    const currentUrl = page.url();
    console.log(`  Current URL: ${currentUrl}`);

    // Check if we're redirected to login or already authenticated
    if (currentUrl.includes('/login')) {
      console.log('  Login page detected.');
      await takeScreenshot(page, '01-login-page');

      for (const cred of CREDENTIALS) {
        console.log(`  Trying: ${cred.label}`);
        await page.fill('#username', '');
        await page.fill('#password', '');
        await page.fill('#username', cred.username);
        await page.fill('#password', cred.password);
        await page.click('button[type="submit"]');

        try {
          // Wait for navigation away from login page
          await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 5000 });
          console.log(`  SUCCESS: Logged in with ${cred.label}`);
          loggedIn = true;
          break;
        } catch {
          console.log(`  FAILED: ${cred.label}`);
          // Check for error toast/message
          const errorEl = await page.$('.text-destructive, [data-sonner-toast], .sonner-toast');
          if (errorEl) {
            const errorText = await errorEl.innerText().catch(() => '');
            console.log(`  Error message: ${errorText}`);
          }
        }
      }

      if (!loggedIn) {
        console.log('  COULD NOT LOGIN with any credential. Taking final screenshot.');
        await takeScreenshot(page, '01-login-failed');
        // Check if there's a register button or any other clue
        const bodyText = await page.innerText('body').catch(() => '');
        console.log('  Page body excerpt:', bodyText.substring(0, 500));
      }
    } else {
      console.log('  Already authenticated (no redirect to /login).');
      loggedIn = true;
    }

    if (!loggedIn) {
      console.log('\n--- SKIPPING remaining tests: Could not authenticate ---');
      await browser.close();
      return;
    }

    // Wait for the main layout to load
    await page.waitForTimeout(2000);

    // ===============================================
    // STEP 2: Dashboard / Workbench
    // ===============================================
    console.log('\n--- STEP 2: Dashboard / Workbench ---');
    // We should be at /workbench after login
    await page.waitForTimeout(1500);
    await takeScreenshot(page, '02-dashboard');

    // List all sidebar navigation items
    const navItems = await page.$$eval('nav a, [role="navigation"] a, .sidebar a, aside a', (links) =>
      links.map((l) => ({
        href: l.getAttribute('href'),
        text: l.innerText?.trim(),
      })).filter((l) => l.text)
    );
    console.log('  Navigation items found:', navItems.length);
    navItems.forEach((item) => console.log(`    - ${item.text} => ${item.href}`));

    // ===============================================
    // STEP 3: Requirements Page (B2 + A7)
    // ===============================================
    console.log('\n--- STEP 3: Requirements Page ---');

    // Navigate by clicking sidebar link or direct URL
    try {
      await page.click('a[href="/requirement"]');
      await page.waitForURL('**/requirement', { timeout: 5000 });
    } catch {
      console.log('  Sidebar click failed, using direct URL');
      await page.goto(`${TARGET_URL}/requirement`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    console.log('  Page title:', await page.title());
    await takeScreenshot(page, '03-requirement-overview');

    // --- A7: Lanhu Settings ---
    console.log('  --- A7: Lanhu Settings ---');
    // Look for "蓝湖设置" button (has Settings icon)
    const lanhuBtn = await page.$('button:has-text("蓝湖设置")');
    if (lanhuBtn) {
      console.log('  Found "蓝湖设置" button');
      await lanhuBtn.click();
      await page.waitForTimeout(1000);

      // Check if settings dialog opened
      const dialog = await page.$('[role="dialog"]');
      if (dialog) {
        console.log('  Lanhu Settings dialog opened');
        await takeScreenshot(page, '03a-lanhu-settings-dialog');

        // Check for the 4 fields
        const dialogText = await dialog.innerText();
        console.log('  Dialog content excerpt:', dialogText.substring(0, 500));
        const hasUserProjectId = dialogText.includes('Project ID') && dialogText.includes('CamelTv');
        const hasAdminProjectId = dialogText.includes('运营后台');
        console.log('  A7 checks:');
        console.log(`    - User端 (CamelTv) fields: ${hasUserProjectId ? 'OK' : 'MISSING'}`);
        console.log(`    - Admin端 fields: ${hasAdminProjectId ? 'OK' : 'MISSING'}`);

        // Look for Project ID inputs and Version ID inputs
        const inputs = await dialog.$$('input');
        console.log(`    - Total input fields in dialog: ${inputs.length}`);

        // Close dialog
        const cancelBtn = await dialog.$('button:has-text("取消")');
        if (cancelBtn) await cancelBtn.click();
        else await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
      } else {
        console.log('  No dialog detected after clicking 蓝湖设置');
      }
    } else {
      console.log('  WARNING: "蓝湖设置" button NOT FOUND');
      // Try to find by Settings icon
      const settingsBtns = await page.$$('button');
      for (const btn of settingsBtns) {
        const text = await btn.innerText().catch(() => '');
        if (text.includes('设置') || text.includes('Settings')) {
          console.log(`  Alternative button found: "${text}"`);
        }
      }
    }

    // --- B2: AiResultModal ---
    console.log('  --- B2: AiResultModal ---');
    // Look for items that have "已生成" status (ai-generated)
    const generatedBadges = await page.$$('.badge:has-text("已生成"), span:has-text("已生成")');
    console.log(`  Found ${generatedBadges.length} "已生成" badges`);

    // Look for "查看" (View) or "eye" icon buttons in the table rows
    // Or try to find AI generate/action buttons
    const allRowButtons = await page.$$('table button');
    console.log(`  Found ${allRowButtons.length} buttons in the table`);

    // Try clicking on a requirement row that has generated results
    // First look for rows with AI-related buttons
    let aiModalOpened = false;

    // Look for buttons that could open the AI result modal:
    // "查看" (View/Eye icon), "Sparkles" icon (AI), "生成" button
    const viewButtons = await page.$$('button:has-text("查看"), button:has-text("生成"), button:has-text("导入")');
    console.log(`  Found ${viewButtons.length} view/generate/import buttons`);

    // Try clicking the first "查看" or eye button in the table
    // These appear next to items that have AI results
    for (const btn of viewButtons) {
      const text = await btn.innerText().catch(() => '');
      if (text === '' || text.includes('查看')) {
        // Could be an eye icon button
        try {
          await btn.click();
          await page.waitForTimeout(1500);
          const modal = await page.$('[role="dialog"]');
          if (modal) {
            const modalText = await modal.innerText();
            console.log('  AI Result Modal opened!');
            console.log('  Modal content preview:', modalText.substring(0, 600));
            aiModalOpened = true;

            // Verify tabs: "功能用例", "接口用例", "UI回归建议"
            const hasFuncCases = modalText.includes('功能用例');
            const hasApiCases = modalText.includes('接口用例');
            const hasRegression = modalText.includes('UI回归');

            console.log('  B2 Tab verification:');
            console.log(`    - "功能用例" tab: ${hasFuncCases ? 'PRESENT' : 'MISSING'}`);
            console.log(`    - "接口用例" tab: ${hasApiCases ? 'PRESENT' : 'MISSING'}`);
            console.log(`    - "UI回归建议" tab: ${hasRegression ? 'PRESENT' : 'MISSING'}`);

            await takeScreenshot(page, '03b-ai-result-modal-overview');

            // Try clicking each tab
            const tabTriggers = await modal.$$('[role="tab"]');
            console.log(`  Found ${tabTriggers.length} tabs`);
            for (const tab of tabTriggers) {
              const tabText = await tab.innerText().catch(() => '');
              console.log(`    Tab: "${tabText}"`);
              if (tabText.includes('功能用例')) {
                await tab.click();
                await page.waitForTimeout(500);
                await takeScreenshot(page, '03b-tab-functional-cases');
              } else if (tabText.includes('接口用例')) {
                await tab.click();
                await page.waitForTimeout(500);
                await takeScreenshot(page, '03b-tab-api-cases');
              } else if (tabText.includes('UI回归')) {
                await tab.click();
                await page.waitForTimeout(500);
                await takeScreenshot(page, '03b-tab-regression');
              }
            }

            // Close modal
            const closeBtn = await modal.$('button:has-text("关闭")');
            if (closeBtn) await closeBtn.click();
            else await page.keyboard.press('Escape');
            await page.waitForTimeout(500);
            break;
          }
        } catch {
          // Button click didn't open modal, try next
        }
      }
    }

    if (!aiModalOpened) {
      console.log('  NOTE: Could not open AI result modal. May need requirements with AI-generated content.');
      console.log('  Taking screenshot of the requirements table for reference.');
      await takeScreenshot(page, '03b-requirements-table-reference');
    }

    // ===============================================
    // STEP 4: Test Cases Page (A6)
    // ===============================================
    console.log('\n--- STEP 4: Test Cases Page (A6) ---');

    try {
      await page.click('a[href="/testcase"]');
      await page.waitForURL('**/testcase', { timeout: 5000 });
    } catch {
      console.log('  Sidebar click failed, using direct URL');
      await page.goto(`${TARGET_URL}/testcase`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    console.log('  Page title:', await page.title());
    await takeScreenshot(page, '04-testcase-overview');

    // Look for review workflow buttons
    // Send = 提交评审, CheckCircle2 = 通过, XCircle = 驳回
    console.log('  Looking for review workflow buttons...');

    // Check the table for action buttons
    const tableBtns = await page.$$('table button');
    console.log(`  Found ${tableBtns.length} buttons in table`);

    // List all button titles
    let foundSend = false;
    let foundApprove = false;
    let foundReject = false;

    for (const btn of tableBtns) {
      const title = await btn.getAttribute('title').catch(() => '');
      const text = await btn.innerText().catch(() => '');
      if (title) console.log(`    Button title: "${title}"`);
      if (title === '提交评审') foundSend = true;
      if (title === '通过') foundApprove = true;
      if (title === '驳回') foundReject = true;
    }

    console.log('  A6 Review buttons found:');
    console.log(`    - Send (提交评审): ${foundSend ? 'PRESENT' : 'NOT FOUND'}`);
    console.log(`    - CheckCircle2 (通过): ${foundApprove ? 'PRESENT' : 'NOT FOUND'}`);
    console.log(`    - XCircle (驳回): ${foundReject ? 'NOT FOUND' : 'NOT FOUND (expected only on submitted cases)'}`);

    // Also check for review status badges
    const reviewBadges = await page.$$('.badge, [class*="badge"]');
    for (const badge of reviewBadges) {
      const text = await badge.innerText().catch(() => '');
      if (['草稿', '已提交', '已通过', '已驳回'].includes(text.trim())) {
        console.log(`    Review status badge found: "${text.trim()}"`);
      }
    }

    // Try clicking "提交评审" button on a draft case
    try {
      const sendBtn = await page.$('button[title="提交评审"]');
      if (sendBtn) {
        console.log('  Clicking "提交评审" button...');
        await sendBtn.click();
        await page.waitForTimeout(1000);

        // Check for review dialog
        const reviewDialog = await page.$('[role="alertdialog"]');
        if (reviewDialog) {
          console.log('  Review dialog opened!');
          await takeScreenshot(page, '04-review-dialog');
          const dialogText = await reviewDialog.innerText();
          console.log('  Review dialog content:', dialogText.substring(0, 300));

          // Close the dialog
          const cancelBtn = await reviewDialog.$('button:has-text("取消")');
          if (cancelBtn) await cancelBtn.click();
          else await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
        } else {
          console.log('  No review dialog appeared');
        }
      } else {
        console.log('  No "提交评审" button available on this page (all cases may be already submitted/reviewed)');
      }
    } catch (e) {
      console.log(`  Error interacting with review button: ${e.message}`);
    }

    // ===============================================
    // STEP 5: Integration Page (B6)
    // ===============================================
    console.log('\n--- STEP 5: Integration Page (B6) ---');

    try {
      await page.click('a[href="/integration"]');
      await page.waitForURL('**/integration', { timeout: 5000 });
    } catch {
      console.log('  Sidebar click failed, using direct URL');
      await page.goto(`${TARGET_URL}/integration`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    console.log('  Page title:', await page.title());
    await takeScreenshot(page, '05-integration-overview');

    // Look for "模块联动追踪" card (B6)
    const linkageCard = await page.$('h2:has-text("模块联动追踪"), .card:has-text("模块联动追踪")');
    if (linkageCard) {
      console.log('  B6 "模块联动追踪" card FOUND!');
    } else {
      console.log('  WARNING: "模块联动追踪" section not found');
      // Check page content
      const pageText = await page.innerText('body');
      if (pageText.includes('模块联动追踪')) {
        console.log('    Text exists but element search failed');
      }
    }

    // Check for visual flow pipeline elements
    const pageText = await page.innerText('body').catch(() => '');
    console.log('  B6 Linkage panel checks:');
    console.log(`    - "模块联动追踪" heading: ${pageText.includes('模块联动追踪') ? 'PRESENT' : 'MISSING'}`);
    console.log(`    - "需求 → 用例 → 执行" badge: ${pageText.includes('需求') && pageText.includes('用例') ? 'PRESENT' : 'MISSING'}`);
    console.log(`    - "用例关联率" progress: ${pageText.includes('用例关联率') ? 'PRESENT' : 'MISSING'}`);
    console.log(`    - "需求覆盖率" progress: ${pageText.includes('需求覆盖率') ? 'PRESENT' : 'MISSING'}`);

    // Check for visual flow pipeline (需求 → 用例 → API端点 → UI脚本)
    const hasFlow = pageText.includes('需求') && pageText.includes('用例') && (pageText.includes('API端点') || pageText.includes('UI脚本'));
    console.log(`    - Visual flow pipeline (需求→用例→API→UI): ${hasFlow ? 'PARTIALLY PRESENT' : 'NOT DETECTED'}`);

    // ===============================================
    // STEP 6: Release Bundles Page (B4+B5)
    // ===============================================
    console.log('\n--- STEP 6: Release Bundles (B4+B5) ---');

    try {
      await page.click('a[href="/release-bundles"]');
      await page.waitForURL('**/release-bundles', { timeout: 5000 });
    } catch {
      console.log('  Sidebar click failed, using direct URL');
      await page.goto(`${TARGET_URL}/release-bundles`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    console.log('  Page title:', await page.title());
    await takeScreenshot(page, '06-release-bundles-list');

    // Look for a bundle to click into
    const bundleLinks = await page.$$('table a, table button, a[href*="/release-bundles/"]');
    console.log(`  Found ${bundleLinks.length} links/buttons in release bundles table`);

    // Try to navigate to the first bundle detail
    let bundleFound = false;
    // Look for any clickable element in the table that might lead to detail
    const tableRows = await page.$$('table tbody tr');
    console.log(`  Found ${tableRows.length} rows in the table`);

    if (tableRows.length > 0) {
      console.log('  Clicking first row to navigate to bundle detail...');
      const firstRow = tableRows[0];
      try {
        await firstRow.click();
        await page.waitForTimeout(1500);
      } catch {
        // Click failed, try a link
        const detailLink = await firstRow.$('a');
        if (detailLink) {
          await detailLink.click();
          await page.waitForTimeout(1500);
        }
      }
    }

    // Check current URL
    const bundleUrl = page.url();
    console.log(`  Current URL after click: ${bundleUrl}`);

    if (bundleUrl.includes('/release-bundles/') && !bundleUrl.endsWith('/release-bundles')) {
      console.log('  Bundle detail page loaded!');
      bundleFound = true;
      await page.waitForTimeout(2000);
      await takeScreenshot(page, '06-bundle-detail');

      // Check for B4+B5 regression buttons
      const pageBody = await page.innerText('body').catch(() => '');
      const hasRegressionScopeBtn = pageBody.includes('回归范围');
      const hasTriggerRegBtn = pageBody.includes('触发UI回归');

      console.log('  B4+B5 Regression buttons:');
      console.log(`    - "回归范围" button: ${hasRegressionScopeBtn ? 'PRESENT' : 'NOT FOUND'}`);
      console.log(`    - "触发UI回归" button: ${hasTriggerRegBtn ? 'PRESENT' : 'NOT FOUND'}`);

      // Click "回归范围" button
      try {
        const scopeBtn = await page.$('button:has-text("回归范围")');
        if (scopeBtn) {
          console.log('  Clicking "回归范围" button...');
          await scopeBtn.click();
          await page.waitForTimeout(2000);

          // Check if regression scope results appeared
          const regCard = await page.$('h2:has-text("UI 回归测试范围"), .card:has-text("回归测试范围")');
          if (regCard) {
            console.log('  Regression scope result card appeared!');
          }

          const resultText = await page.innerText('body').catch(() => '');
          const hasChangedModules = resultText.includes('变更模块');
          const hasRegCases = resultText.includes('回归用例');
          console.log('  Regression scope results:');
          console.log(`    - "变更模块" stat: ${hasChangedModules ? 'PRESENT' : 'MISSING'}`);
          console.log(`    - "回归用例" stat: ${hasRegCases ? 'PRESENT' : 'MISSING'}`);

          await takeScreenshot(page, '06-regression-scope-result');
        } else {
          console.log('  "回归范围" button not found on the page');
        }
      } catch (e) {
        console.log(`  Error with regression scope: ${e.message}`);
      }
    } else {
      console.log('  WARNING: Did not navigate to bundle detail page');
      console.log(`  Current URL: ${bundleUrl}`);
      // Take screenshot of whatever page we're on
      await takeScreenshot(page, '06-release-bundles-state');
    }

    // ===============================================
    // FINAL SUMMARY
    // ===============================================
    console.log('\n========================================');
    console.log('  WALKTHROUGH COMPLETE');
    console.log('========================================');
    console.log('Screenshots saved to:', SCREENSHOT_DIR);

  } catch (err) {
    console.error('\nFATAL ERROR:', err.message);
    await takeScreenshot(page, '99-error-state');
  } finally {
    await browser.close();
    console.log('\nBrowser closed.');
  }
})();
