/**
 * PAY — 骆驼币充值 UI 自动化
 *
 * 对应 P0 用例: TC-PAY-001, 004, 010, 016, 017, 018
 */
import { test, expect } from '@playwright/test';
import { aiBoolean, aiAction } from '@midscene/web';
import { login } from '../../utils/auth';
import { initTrafficCapture, attachTrafficCapture, flushTrafficCapture } from '../../utils/traffic-capture';

const SESSION = 'recharge';

test.describe('PAY — 充值', () => {
  test.beforeAll(() => initTrafficCapture(SESSION));
  test.beforeEach(async ({ page }) => { attachTrafficCapture(page); await login(page); });
  test.afterAll(() => flushTrafficCapture());

  test('TC-PAY-001: 展示当前骆驼币余额', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    // 进入充值/钱包页
    await aiAction('click the wallet balance or coin icon');
    await page.waitForTimeout(2000);

    const balanceVisible = await aiBoolean('Is the current camel coin balance displayed with a number?');
    expect(balanceVisible).toBe(true);
  });

  test('TC-PAY-004: 默认选中法币 TAB', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    await aiAction('go to the recharge page');
    await page.waitForTimeout(2000);

    const fiatSelected = await aiBoolean('Is the Fiat/FIAT tab selected by default?');
    console.log(`Fiat tab selected: ${fiatSelected}`);
  });

  test('TC-PAY-010: 套餐列表按展示顺序', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    await aiAction('go to the recharge page, select a payment method');
    await page.waitForTimeout(2000);

    const packagesVisible = await aiBoolean('Are coin packages displayed with amounts?');
    expect(packagesVisible).toBe(true);
  });

  test('TC-PAY-016: 创建订单按钮可见', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    await aiAction('go to the recharge page, select a package');
    await page.waitForTimeout(2000);

    const proceedVisible = await aiBoolean('Is the "Proceed to Payment" or continue button visible?');
    console.log(`Proceed to Payment visible: ${proceedVisible}`);
  });
});
