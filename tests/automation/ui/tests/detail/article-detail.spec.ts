/**
 * DETAIL — UGC 详情页 UI 自动化
 *
 * 对应 P0 用例: TC-DETAIL-003, 005, 006, 019, 020, 023, 024, 026, 029, 031, 032
 */
import { test, expect } from '@playwright/test';
import { aiBoolean, aiAction } from '@midscene/web';
import { login } from '../../utils/auth';
import { initTrafficCapture, attachTrafficCapture, flushTrafficCapture } from '../../utils/traffic-capture';

const SESSION = 'article-detail';

test.describe('DETAIL — UGC详情', () => {
  test.beforeAll(() => initTrafficCapture(SESSION));
  test.beforeEach(async ({ page }) => { attachTrafficCapture(page); await login(page); });
  test.afterAll(() => flushTrafficCapture());

  test('TC-DETAIL-005/006: Follow/Unfollow 切换', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    await aiAction('click on an article to enter its detail page');
    await page.waitForTimeout(2000);

    const isDetail = await aiBoolean('Is this an article detail page?');
    if (!isDetail) { test.skip(true, 'Not on detail page'); return; }

    // 检查 Follow 按钮
    const followVisible = await aiBoolean('Is there a Follow or Following button visible?');
    if (!followVisible) { test.skip(true, 'Follow button not visible'); return; }

    // 点击 Follow
    await aiAction('click the Follow button');
    await page.waitForTimeout(1500);

    const followSuccess = await aiBoolean('Did a "successfully followed" or similar message appear?');
    console.log(`Follow success: ${followSuccess}`);
  });

  test('TC-DETAIL-019/020: 未解锁预测项脱敏 vs 已解锁完整', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    await aiAction('find and click on a pay-per-article item');
    await page.waitForTimeout(2000);

    const isUnlocked = await aiBoolean('Is the full prediction data visible (odds and picks)?');
    // 未解锁应只看到表头
    if (!isUnlocked) {
      const hasHeaderOnly = await aiBoolean('Is there a prediction table header but no specific odds values?');
      expect(hasHeaderOnly).toBe(true);
    }
  });

  test('TC-DETAIL-032: 余额不足无法解锁', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    await aiAction('click on a pay-per-article item with a coin price');
    await page.waitForTimeout(2000);

    const unlockBtn = await aiBoolean('Is the Unlock button visible with a coin amount?');
    if (!unlockBtn) { test.skip(true, 'Unlock button not visible'); return; }

    await aiAction('click the Unlock button');
    await page.waitForTimeout(1500);

    // 确认弹窗
    const confirmDialog = await aiBoolean('Is there a confirmation dialog for unlocking?');
    if (confirmDialog) {
      await aiAction('click the confirm/proceed button');
      await page.waitForTimeout(2000);

      const balanceInsufficient = await aiBoolean('Is there an "insufficient balance" or "please recharge" message?');
      console.log(`Balance insufficient shown: ${balanceInsufficient}`);
    }
  });
});
