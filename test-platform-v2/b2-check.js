// Quick B2 fix — wait for AI generation to complete
const { chromium } = require('playwright');
const path = require('path');
const SS = 'C:/Users/26029/.claude/skills/playwright-skill/screenshots';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 80 });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 5000 });
  await page.waitForTimeout(2000);

  await page.goto('http://localhost:5173/requirement', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  console.log('Looking for "AI 生成" buttons...');
  const aiBtns = await page.$$('button:has-text("AI 生成")');
  console.log(`Found ${aiBtns.length} AI 生成 buttons`);

  // For each "AI 生成" button, try to trigger generation and wait for modal
  for (let i = 0; i < aiBtns.length; i++) {
    console.log(`\nTrying AI生成 button ${i + 1}...`);
    const btn = aiBtns[i];

    // Get the row context
    const row = await btn.evaluateHandle((el) => el.closest('tr'));
    if (row) {
      const rowText = await row.evaluate((el) => el.innerText);
      console.log(`  Row: ${rowText.substring(0, 120)}`);
    }

    try {
      await btn.scrollIntoViewIfNeeded();
      await btn.click();
      console.log('  Clicked AI生成. Waiting for dialog (up to 30s)...');

      // Wait for a dialog to appear - AI generation takes time
      let dialog = null;
      for (let j = 0; j < 30; j++) {
        await page.waitForTimeout(1000);
        dialog = await page.$('[role="dialog"]');
        if (dialog) {
          const visible = await dialog.isVisible();
          if (visible) break;
        }
        if (j % 5 === 4) console.log(`  Still waiting... (${j + 1}s)`);
      }

      if (dialog) {
        const dialogText = await dialog.innerText();
        console.log(`  Dialog text (first 300 chars): ${dialogText.substring(0, 300)}`);

        // Check if it's the AiResultModal
        if (dialogText.includes('功能用例') || dialogText.includes('功能拆分') || dialogText.includes('AI 生成功能测试用例')) {
          console.log('  *** AiResultModal FOUND! ***');

          // Check tabs
          const tabs = await dialog.$$('[role="tab"]');
          const tabNames = [];
          for (const t of tabs) {
            const name = await t.innerText().catch(() => '');
            tabNames.push(name);
          }
          console.log(`  Tabs (${tabs.length}): ${JSON.stringify(tabNames)}`);

          // Screenshot full modal
          await page.screenshot({ path: path.join(SS, 'b2-ai-result-modal-full.png'), fullPage: true });

          // Screenshot each tab
          for (const t of tabs) {
            try {
              await t.click();
              await page.waitForTimeout(800);
              const name = await t.innerText().catch(() => '');
              const safe = name.replace(/[^a-zA-Z\u4e00-\u9fff0-9]/g, '-').slice(0, 30);
              await page.screenshot({ path: path.join(SS, `b2-tab-${safe}.png`), fullPage: true });
              console.log(`  Screenshot: tab "${name}"`);
            } catch (e) {
              console.log(`  Tab click error: ${e.message}`);
            }
          }

          // Check for B2 tab verification
          const hasFunc = dialogText.includes('功能用例');
          const hasApi = dialogText.includes('接口用例');
          const hasReg = dialogText.includes('UI回归') || dialogText.includes('集成功能点');
          console.log(`\n  B2 VERIFICATION:`);
          console.log(`  "功能用例" tab: ${hasFunc ? 'PRESENT' : 'MISSING'}`);
          console.log(`  "接口用例" tab: ${hasApi ? 'PRESENT' : 'MISSING'}`);
          console.log(`  "UI回归建议" tab: ${hasReg ? 'PRESENT' : 'MISSING'}`);

          // Close
          const closeBtn = await dialog.$('button:has-text("关闭")');
          if (closeBtn) await closeBtn.click();
          else await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
          break;
        } else {
          console.log('  Not the AiResultModal. Closing...');
          await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
        }
      } else {
        console.log('  No dialog appeared after 30s');
      }
    } catch (e) {
      console.log(`  Error: ${e.message}`);
    }
  }

  await browser.close();
  console.log('\nDone.');
})();
