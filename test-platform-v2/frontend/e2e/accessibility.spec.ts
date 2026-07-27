import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test('login page has no automatically detectable WCAG A/AA violations', async ({ page }) => {
  await page.goto('/login')
  await expect(page.locator('button[type="submit"]')).toBeVisible()

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()

  expect(results.violations).toEqual([])
})
