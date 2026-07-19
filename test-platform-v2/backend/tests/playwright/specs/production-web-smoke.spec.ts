import { test, expect } from '@playwright/test';

const SITE_URL = process.env.BASE_URL || 'https://www.camel1.tv';
const USERNAME = process.env.PROD_PHONE || '';
const PASSWORD = process.env.PROD_PASSWORD || '';

test('CamelTv 生产首页与授权登录入口只读冒烟', async ({ page }) => {
  test.setTimeout(60_000);
  page.setDefaultTimeout(10_000);
  page.setDefaultNavigationTimeout(20_000);

  const homeResponse = await page.goto(SITE_URL, { waitUntil: 'domcontentloaded' });
  expect(homeResponse?.status() || 0).toBeLessThan(400);
  expect((await page.title()).trim().length).toBeGreaterThan(0);
  expect(await page.locator('a[href], button, [role="button"]').count()).toBeGreaterThan(0);
  await page.screenshot({ path: test.info().outputPath('prod-homepage.png'), fullPage: false });

  if (!USERNAME || !PASSWORD) {
    test.info().annotations.push({ type: 'authorization', description: '未配置 PROD_PHONE/PROD_PASSWORD，跳过登录步骤' });
    return;
  }

  const loginUrl = new URL('/login', SITE_URL).toString();
  await page.goto(loginUrl, { waitUntil: 'domcontentloaded' });

  const phoneInput = page.locator('input[type="tel"], input[name*="phone"], input[name*="username"], input[type="text"]').first();
  const passwordInput = page.locator('input[type="password"]').first();
  if (await phoneInput.isVisible().catch(() => false)) await phoneInput.fill(USERNAME);
  if (await passwordInput.isVisible().catch(() => false)) await passwordInput.fill(PASSWORD);

  const submit = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Sign In")').first();
  if (await submit.isVisible().catch(() => false)) {
    await submit.click();
    await page.waitForTimeout(2500);
  }
  await page.screenshot({ path: test.info().outputPath('prod-login-result.png'), fullPage: false });
  expect(page.url()).toMatch(/^https:\/\/(www\.)?camel1\.tv\//);
});
