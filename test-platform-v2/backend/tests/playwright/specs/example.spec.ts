import { test, expect } from '@playwright/test';

test.describe('CamelTv 示例测试套件', () => {

  test('首页可访问', async ({ page }) => {
    // 替换为实际的测试逻辑
    await page.goto('/');
    await expect(page).toHaveTitle(/CamelTv/);
  });

  test('登录页面正常加载', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="text"]').first()).toBeVisible();
  });

});
