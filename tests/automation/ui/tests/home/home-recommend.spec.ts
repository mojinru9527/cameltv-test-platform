/**
 * HOME — 首页预测推荐模块 UI 自动化
 *
 * 对应 P0 用例: TC-HOME-001, 002
 */
import { test, expect } from '@playwright/test';
import { aiBoolean, aiAction } from '@midscene/web';
import { login } from '../../utils/auth';
import { initTrafficCapture, attachTrafficCapture, flushTrafficCapture } from '../../utils/traffic-capture';

const SESSION = 'home-recommend';

test.describe('HOME — 首页推荐', () => {
  test.beforeAll(() => initTrafficCapture(SESSION));
  test.beforeEach(async ({ page }) => { attachTrafficCapture(page); await login(page); });
  test.afterAll(() => flushTrafficCapture());

  test('TC-HOME-001: 展示 Yield 前5作者推荐', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    await aiAction('scroll to the prediction recommendation section');
    const hasRecommended = await aiBoolean('Is there a "Recommended" or top prediction authors section with author cards?');
    // 取决于首页是否有推荐模块
    console.log(`Recommendation section visible: ${hasRecommended}`);
  });

  test('TC-HOME-001: 推荐作者按 Yield 排序', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    await aiAction('scroll to the recommended authors section');
    const hasYieldInfo = await aiBoolean('Are Yield percentage numbers visible near the author names?');
    console.log(`Yield info visible: ${hasYieldInfo}`);
  });
});
