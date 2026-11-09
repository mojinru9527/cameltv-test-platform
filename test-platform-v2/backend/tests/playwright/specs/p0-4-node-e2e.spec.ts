import { test, expect } from '@playwright/test';

test('p0-4 node e2e', async ({ page }) => {
  await page.goto('data:text/html,<h1 id="t">p0-4 ok</h1>');
  await expect(page.locator('#t')).toHaveText('p0-4 ok');
});
