// Batch-34 Frontend Walkthrough v2 — Improved selectors for shadcn sidebar + Radix UI
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const TARGET_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = path.join('C:/Users/26029/.claude/skills/playwright-skill/screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function ssPath(name) {
  return path.join(SCREENSHOT_DIR, `batch34-v2-${name}.png`);
}

async function takeScreenshot(page, name, fullPage = true) {
  const fp = ssPath(name);
  await page.screenshot({ path: fp, fullPage });
  console.log(`  [screenshot] ${fp}`);
}

// Navigate using the sidebar button by text content
async function navigateViaSidebar(page, menuText) {
  console.log(`  Navigating to: ${menuText}`);
  // SidebarMenuButton renders as button[data-sidebar="menu-button"]
  const buttons = await page.$$('button[data-sidebar="menu-button"]');
  for (const btn of buttons) {
    const text = await btn.innerText().catch(() => '');
    if (text.includes(menuText)) {
      await btn.click();
      await page.waitForTimeout(1500);
      return true;
    }
  }
  // Try collapsed tooltip or aria-label fallback
  const allBtns = await page.$$('nav button, aside button');
  for (const btn of allBtns) {
    const aria = await btn.getAttribute('aria-label').catch(() => '');
    const text = await btn.innerText().catch(() => '');
    if (text.includes(menuText) || aria.includes(menuText)) {
      await btn.click();
      await page.waitForTimeout(1500);
      return true;
    }
  }
  return false;
}

async function logPageState(page, label) {
  const url = page.url();
  const title = await page.title().catch(() => '?');
  console.log(`  [${label}] URL: ${url} | Title: ${title}`);
}

(async () => {
  console.log('========================================');
  console.log('  Batch-34 Frontend Walkthrough v2');
  console.log(`  Target: ${TARGET_URL}`);
  console.log('========================================\n');

  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  const page = await context.newPage();

  let loggedIn = false;

  try {
    // ===============================================
    // STEP 1: Login
    // ===============================================
    console.log('\n=== STEP 1: Login ===');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1000);

    const currentUrl = page.url();
    console.log(`  Current URL: ${currentUrl}`);

    if (currentUrl.includes('/login')) {
      console.log('  Login page detected.');
      await takeScreenshot(page, '01-login-page');

      for (const cred of [
        { username: 'admin', password: 'admin123' },
        { username: 'tester', password: 'tester123' },
        { username: 'test', password: 'test123' },
      ]) {
        console.log(`  Trying: ${cred.username}/${cred.password}`);
        try {
          await page.fill('#username', '');
          await page.fill('#password', '');
          await page.fill('#username', cred.username);
          await page.fill('#password', cred.password);
          await page.click('button[type="submit"]');
          await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 5000 });
          console.log(`  SUCCESS: Logged in as ${cred.username}`);
          loggedIn = true;
          break;
        } catch {
          console.log(`  FAILED: ${cred.username}`);
        }
      }
    } else {
      console.log('  Already authenticated.');
      loggedIn = true;
    }

    if (!loggedIn) {
      console.log('  COULD NOT LOGIN. Aborting.');
      await takeScreenshot(page, '01-login-failed');
      await browser.close();
      return;
    }

    await page.waitForTimeout(2000);

    // ===============================================
    // STEP 2: Dashboard / Workbench
    // ===============================================
    console.log('\n=== STEP 2: Dashboard (Workbench) ===');
    await logPageState(page, 'dashboard');
    await takeScreenshot(page, '02-dashboard-full');

    // List all sidebar navigation buttons
    const sidebarButtons = await page.$$('button[data-sidebar="menu-button"]');
    console.log(`  Sidebar menu buttons: ${sidebarButtons.length}`);
    for (const btn of sidebarButtons) {
      const text = await btn.innerText().catch(() => '');
      console.log(`    ${text ? `"${text}"` : '(empty - likely collapsed)'}`);
    }

    // ===============================================
    // STEP 3: Requirements Page (B2 + A7)
    // ===============================================
    console.log('\n=== STEP 3: Requirements Page ===');
    const navReq = await navigateViaSidebar(page, '需求文档');
    if (!navReq) {
      console.log('  Sidebar nav failed, using direct URL');
      await page.goto(`${TARGET_URL}/requirement`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    await logPageState(page, 'requirements');
    await takeScreenshot(page, '03-requirements-overview');

    // --- A7: Lanhu Settings ---
    console.log('\n  --- A7: Lanhu Settings ---');
    // The button should be in the header area with text "蓝湖设置"
    // It uses the Settings icon component
    const allButtons = await page.$$('button');
    let lanhuSettingsFound = false;
    for (const btn of allButtons) {
      const text = await btn.innerText().catch(() => '');
      if (text.includes('蓝湖设置') || text.includes('蓝湖项目配置')) {
        console.log(`  Found button: "${text}"`);
        await btn.click();
        await page.waitForTimeout(1000);
        const dialog = await page.$('[role="dialog"]');
        if (dialog) {
          console.log('  Lanhu Settings dialog OPENED!');
          await takeScreenshot(page, '03a-lanhu-settings-dialog');
          const dialogText = await dialog.innerText();
          console.log('  Dialog content:', dialogText.substring(0, 800));
          // Close
          const cancelBtn = await dialog.$('button:has-text("取消")');
          if (cancelBtn) await cancelBtn.click();
          else await page.keyboard.press('Escape');
          lanhuSettingsFound = true;
        }
        break;
      }
    }
    if (!lanhuSettingsFound) {
      console.log('  WARNING: "蓝湖设置" button NOT found in requirements page header');
      console.log('  This might mean A7 Lanhu Settings is NOT YET IMPLEMENTED');
      // Take a screenshot of the header area
      await takeScreenshot(page, '03a-no-lanhu-settings');
    }

    // --- B2: AiResultModal ---
    console.log('\n  --- B2: AiResultModal ---');
    // Look for requirement rows with AI generation capabilities
    // Try to click "AI生成" / "Sparkles" button on a requirement row
    // Or find rows with "生成" button that triggers AI case generation

    // First, let's see the table structure
    const tableHeaders = await page.$$eval('table th, thead th', (ths) => ths.map((th) => th.innerText?.trim()));
    console.log(`  Table headers: ${JSON.stringify(tableHeaders)}`);

    // Look for AI action buttons in rows
    const rows = await page.$$('table tbody tr');
    console.log(`  Table rows: ${rows.length}`);

    let aiModalOpened = false;

    // Try to find and click an "AI生成" or "生成" button
    for (const row of rows) {
      const rowText = await row.innerText().catch(() => '');
      const rowButtons = await row.$$('button');
      for (const btn of rowButtons) {
        const btnText = await btn.innerText().catch(() => '');
        if (btnText.includes('生成') || btnText.includes('AI') || btnText.includes('查看')) {
          console.log(`  Clicking "${btnText}" on row: ${rowText.substring(0, 80)}...`);
          try {
            await btn.click();
            await page.waitForTimeout(1500);
            const dialog = await page.$('[role="dialog"]');
            if (dialog) {
              const dialogTitle = await dialog.$eval('h2', (el) => el.innerText).catch(() => '');
              console.log(`  Dialog opened with title: "${dialogTitle}"`);
              const dialogText = await dialog.innerText();
              console.log(`  Dialog text preview: ${dialogText.substring(0, 500)}`);

              // Check if this is the AiResultModal or some other dialog
              if (dialogText.includes('功能用例') || dialogText.includes('接口用例') || dialogText.includes('AI 生成')) {
                console.log('  This IS the AiResultModal!');
                aiModalOpened = true;

                // Check for tabs
                const tabs = await dialog.$$('[role="tab"]');
                console.log(`  Found ${tabs.length} tabs in the modal`);
                for (const tab of tabs) {
                  const tabText = await tab.innerText().catch(() => '');
                  console.log(`    Tab: "${tabText}"`);
                }

                // Check specific B2 tabs
                const hasFuncTab = dialogText.includes('功能用例');
                const hasApiTab = dialogText.includes('接口用例');
                const hasRegTab = dialogText.includes('UI回归') || dialogText.includes('集成功能点');

                console.log('  B2 Tab verification:');
                console.log(`    "功能用例" tab: ${hasFuncTab ? 'PRESENT' : 'MISSING'}`);
                console.log(`    "接口用例" tab: ${hasApiTab ? 'PRESENT' : 'MISSING'}`);
                console.log(`    "UI回归建议" tab: ${hasRegTab ? 'PRESENT' : 'MISSING'}`);

                await takeScreenshot(page, '03b-ai-result-modal-overview');

                // Try clicking each tab
                for (const tab of tabs) {
                  const tabText = await tab.innerText().catch(() => '');
                  if (tabText.includes('功能用例')) {
                    await tab.click();
                    await page.waitForTimeout(500);
                    await takeScreenshot(page, '03b-tab-functional-cases');
                  } else if (tabText.includes('接口用例')) {
                    await tab.click();
                    await page.waitForTimeout(500);
                    await takeScreenshot(page, '03b-tab-api-cases');
                  } else if (tabText.includes('回归') || tabText.includes('UI')) {
                    await tab.click();
                    await page.waitForTimeout(500);
                    await takeScreenshot(page, '03b-tab-regression');
                  }
                }

                // Close
                const closeBtn = await dialog.$('button:has-text("关闭")');
                if (closeBtn) await closeBtn.click();
                else await page.keyboard.press('Escape');
                await page.waitForTimeout(500);
                break;
              } else {
                console.log('  This is NOT the AiResultModal (different dialog), closing...');
                // Close whatever dialog this is
                const closeBtn = await page.$('[role="dialog"] button:has-text("关闭"), [role="dialog"] button:has-text("Close"), [role="dialog"] [aria-label="Close"]');
                if (closeBtn) await closeBtn.click();
                else await page.keyboard.press('Escape');
                await page.waitForTimeout(500);
              }
            }
          } catch (e) {
            console.log(`  Error clicking button: ${e.message}`);
          }
        }
      }
      if (aiModalOpened) break;
    }

    if (!aiModalOpened) {
      console.log('  NOTE: Could not find/identify the AI Result Modal');
      console.log('  This may be because: no requirements have AI-generated results, or the button layout differs');
      await takeScreenshot(page, '03b-requirements-table');
    }

    // ===============================================
    // STEP 4: Test Cases Page (A6)
    // ===============================================
    console.log('\n=== STEP 4: Test Cases Page (A6) ===');
    const navTc = await navigateViaSidebar(page, '用例服务');
    if (!navTc) {
      console.log('  Sidebar nav failed, using direct URL');
      await page.goto(`${TARGET_URL}/testcase`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    await logPageState(page, 'testcase');
    await takeScreenshot(page, '04-testcase-overview');

    // Check review workflow buttons
    const tcRows = await page.$$('table tbody tr');
    console.log(`  Test case rows: ${tcRows.length}`);

    let reviewButtonsFound = false;
    for (const row of tcRows) {
      const rowButtons = await row.$$('button');
      for (const btn of rowButtons) {
        const title = await btn.getAttribute('title').catch(() => '');
        if (title && ['提交评审', '通过', '驳回'].includes(title)) {
          console.log(`  Found review button: "${title}"`);
          reviewButtonsFound = true;
        }
      }
    }

    // Also try to find by icon structure (button with specific classes)
    const allTableBtns = await page.$$('table button[title]');
    console.log(`  Buttons with title in table: ${allTableBtns.length}`);
    for (const btn of allTableBtns.slice(0, 30)) {
      const title = await btn.getAttribute('title').catch(() => '');
      if (title) console.log(`    title="${title}"`);
    }

    // Count review status badges
    const draftBadges = await page.$$('text=草稿');
    const submittedBadges = await page.$$('text=已提交');
    const approvedBadges = await page.$$('text=已通过');
    console.log(`  Status counts - draft: ${draftBadges.length}, submitted: ${submittedBadges.length}, approved: ${approvedBadges.length}`);

    // Try to click the first "提交评审" button we can find
    try {
      const submitBtn = await page.$('button[title="提交评审"]');
      if (submitBtn) {
        console.log('  Clicking "提交评审"...');
        await submitBtn.click();
        await page.waitForTimeout(1000);
        const reviewDialog = await page.$('[role="alertdialog"]');
        if (reviewDialog) {
          console.log('  Review dialog OPENED!');
          await takeScreenshot(page, '04-review-dialog');
          // Close
          const cancelBtn = await reviewDialog.$('button:has-text("取消")');
          if (cancelBtn) await cancelBtn.click();
          await page.waitForTimeout(500);
        }
      } else {
        console.log('  No "提交评审" button found - all cases may already be reviewed');
        // Check if the button is rendered but with a different selector
        const sendIcons = await page.$$('svg.lucide-send');
        console.log(`  Send (lucide-send) icons found: ${sendIcons.length}`);
        if (sendIcons.length > 0) {
          console.log('  Send icons exist but button title might differ');
        }
      }
    } catch (e) {
      console.log(`  Review button error: ${e.message}`);
    }

    console.log('  A6 Review workflow check:');
    console.log(`    Review buttons (Send/Approve/Reject) found: ${reviewButtonsFound ? 'YES' : 'NOT FOUND'}`);
    console.log(`    Draft cases available for submission: ${draftBadges.length > 0 ? 'YES' : 'NO'}`);

    // ===============================================
    // STEP 5: Integration Page (B6)
    // ===============================================
    console.log('\n=== STEP 5: Integration Page (B6) ===');
    const navInt = await navigateViaSidebar(page, '集成配置');
    if (!navInt) {
      console.log('  Sidebar nav failed, using direct URL');
      await page.goto(`${TARGET_URL}/integration`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    await logPageState(page, 'integration');
    await takeScreenshot(page, '05-integration-overview');

    const pageText = await page.innerText('body').catch(() => '');
    console.log('  B6 Linkage panel checks:');
    console.log(`    "模块联动追踪" heading: ${pageText.includes('模块联动追踪') ? 'PRESENT' : 'MISSING'}`);
    console.log(`    "用例关联率": ${pageText.includes('用例关联率') ? 'PRESENT' : 'MISSING'}`);
    console.log(`    "需求覆盖率": ${pageText.includes('需求覆盖率') ? 'PRESENT' : 'MISSING'}`);
    console.log(`    Visual flow (需求→用例→API): ${pageText.includes('需求') && pageText.includes('API端点') ? 'PRESENT' : 'MISSING'}`);

    // ===============================================
    // STEP 6: Release Bundles (B4+B5)
    // ===============================================
    console.log('\n=== STEP 6: Release Bundles (B4+B5) ===');
    const navRb = await navigateViaSidebar(page, '版本测试任务');
    if (!navRb) {
      console.log('  Sidebar nav failed, using direct URL');
      await page.goto(`${TARGET_URL}/release-bundles`, { waitUntil: 'networkidle' });
    }
    await page.waitForTimeout(2000);
    await logPageState(page, 'release-bundles');
    await takeScreenshot(page, '06-release-bundles-list');

    // Check if there are any bundles
    const rbPageText = await page.innerText('body').catch(() => '');
    console.log(`  Page content length: ${rbPageText.length} chars`);
    if (rbPageText.includes('暂无') || rbPageText.includes('没有') || rbPageText.includes('empty')) {
      console.log('  NOTE: Page indicates no data (empty state)');
    }

    // Try different selectors for table rows
    const allTableRows = await page.$$('table tbody tr, [role="table"] [role="row"]');
    console.log(`  Table rows found: ${allTableRows.length}`);

    if (allTableRows.length > 0) {
      // Try clicking the first row
      const firstRow = allTableRows[0];
      console.log('  Clicking first row for bundle detail...');
      try {
        // Look for a link in the first row
        const link = await firstRow.$('a');
        if (link) {
          const href = await link.getAttribute('href');
          console.log(`  Link href: ${href}`);
          await link.click();
        } else {
          await firstRow.click();
        }
        await page.waitForTimeout(2000);
        const newUrl = page.url();
        console.log(`  After click URL: ${newUrl}`);

        if (newUrl.includes('/release-bundles/') && !newUrl.endsWith('/release-bundles')) {
          console.log('  Bundle detail page LOADED!');
          await takeScreenshot(page, '06-bundle-detail');

          // B4 + B5: Regression buttons
          const detailText = await page.innerText('body').catch(() => '');
          const hasScopeBtn = detailText.includes('回归范围');
          const hasTriggerBtn = detailText.includes('触发UI回归');
          console.log('  B4+B5 Regression buttons:');
          console.log(`    "回归范围" button: ${hasScopeBtn ? 'PRESENT' : 'NOT FOUND'}`);
          console.log(`    "触发UI回归" button: ${hasTriggerBtn ? 'PRESENT' : 'NOT FOUND'}`);

          // Click regression scope
          try {
            const scopeBtn = await page.$('button:has-text("回归范围")');
            if (scopeBtn) {
              console.log('  Clicking "回归范围"...');
              await scopeBtn.click();
              await page.waitForTimeout(2000);
              const resultText = await page.innerText('body').catch(() => '');
              const hasRegResult = resultText.includes('UI 回归测试范围') || resultText.includes('变更模块');
              console.log(`  Regression scope result: ${hasRegResult ? 'LOADED' : 'NOT LOADED'}`);
              await takeScreenshot(page, '06-regression-scope');
            }
          } catch (e) {
            console.log(`  Regression scope error: ${e.message}`);
          }
        }
      } catch (e) {
        console.log(`  Error navigating to bundle detail: ${e.message}`);
      }
    } else {
      console.log('  NOTE: No release bundles found in database. Cannot test B4+B5.');
    }

    // ===============================================
    console.log('\n========================================');
    console.log('  WALKTHROUGH COMPLETE');
    console.log(`  Screenshots saved to: ${SCREENSHOT_DIR}`);
    console.log('========================================');

  } catch (err) {
    console.error('\nFATAL ERROR:', err.message);
    console.error(err.stack);
    await takeScreenshot(page, '99-error-state');
  } finally {
    await browser.close();
    console.log('\nBrowser closed.');
  }
})();
