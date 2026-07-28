import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const username = process.env.E2E_USERNAME || ''
const password = process.env.E2E_PASSWORD || ''
const hasCredentials = Boolean(username && password)
const THEMES = ['cyberpunk', 'apple', 'clay', 'xlab', 'liquid-glass'] as const

test.describe('Batch 54 real-backend theme acceptance', () => {
  test('login and traverse all five themes without API mocks', async ({ page }) => {
    test.skip(!hasCredentials, '需要通过环境变量注入隔离的本地 E2E 账号')
    test.setTimeout(120_000)

    const businessRequests: string[] = []
    const runtimeErrors: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/')) businessRequests.push(request.url())
    })
    page.on('console', (message) => {
      if (message.type() === 'error') runtimeErrors.push(`console: ${message.text()}`)
    })
    page.on('pageerror', (error) => runtimeErrors.push(`pageerror: ${error.message}`))
    page.on('requestfailed', (request) => runtimeErrors.push(`requestfailed: ${request.url()}`))

    await page.goto('/login')
    await page.fill('input[name="username"]', username)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/workbench/, { timeout: 15_000 })

    for (const theme of THEMES) {
      for (const mode of ['light', 'dark'] as const) {
        await page.evaluate(({ selectedTheme, selectedMode }) => {
          localStorage.setItem('cameltv-theme-color', selectedTheme)
          localStorage.setItem('cameltv-theme-mode', selectedMode)
        }, { selectedTheme: theme, selectedMode: mode })
        const statsResponsePromise = page.waitForResponse(
          (response) => response.url().includes('/api/v1/dashboard/stats')
            && response.request().method() === 'GET',
        )
        await page.reload()
        const statsResponse = await statsResponsePromise
        expect(statsResponse.ok()).toBe(true)
        const statsBody = await statsResponse.json()
        const totalCases = Number(statsBody?.data?.total_cases)
        expect(totalCases).toBeGreaterThanOrEqual(0)
        await expect(page.getByRole('heading', { name: '工作台', level: 1 })).toBeVisible()
        await expect(page.getByText(String(totalCases), { exact: true }).first()).toBeVisible()
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
        await expect(page.locator('html')).toHaveClass(new RegExp(`\\b${mode}\\b`))
        expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1)
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
        expect(axe.violations).toEqual([])
      }
    }

    expect(businessRequests.some((url) => url.includes('/api/v1/auth/login'))).toBe(true)
    expect(businessRequests.some((url) => url.includes('/api/v1/dashboard/stats'))).toBe(true)
    expect(runtimeErrors).toEqual([])
  })

  test('unauthenticated access follows the real 401 recovery path', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()
    try {
      await page.goto('/login')
      const unauthorizedStatus = await page.evaluate(async () => {
        const response = await fetch('/api/v1/dashboard/stats', { credentials: 'include' })
        return response.status
      })
      expect(unauthorizedStatus).toBe(401)
      await page.goto('/workbench')
      await expect(page).toHaveURL(/\/login/, { timeout: 15_000 })
      await expect(page.locator('input[name="username"]')).toBeVisible()
      await expect(page.locator('button[type="submit"]')).toBeVisible()
    } finally {
      await context.close()
    }
  })
})
