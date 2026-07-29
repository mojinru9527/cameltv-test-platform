import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
  { name: 'narrow-mobile', width: 320, height: 568 },
] as const

test.describe('Batch 55 Vite proxy and login shell acceptance', () => {
  test('keeps /apitest in the SPA and proxies only /api/v1', async ({ page }, testInfo) => {
    const runtimeErrors: string[] = []
    const failedRequests: string[] = []

    page.on('console', (message) => {
      if (message.type() === 'error') runtimeErrors.push(`console: ${message.text()}`)
    })
    page.on('pageerror', (error) => runtimeErrors.push(`pageerror: ${error.message}`))
    page.on('requestfailed', (request) => {
      failedRequests.push(`${request.method()} ${request.url()} — ${request.failure()?.errorText ?? 'unknown'}`)
    })

    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })

      const navigation = await page.goto('/apitest')
      expect(navigation?.status()).toBe(200)
      await expect(page).toHaveURL(/\/login$/, { timeout: 10_000 })
      await expect(page.getByRole('heading', { name: 'CamelTv 测试平台', level: 1 })).toBeVisible()
      await expect(page.getByLabel('用户名')).toBeVisible()
      await expect(page.getByLabel('密码')).toBeVisible()
      await expect(page.getByRole('button', { name: '登录' })).toBeVisible()

      const horizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      )
      expect(horizontalOverflow, `${viewport.name} has horizontal overflow`).toBeLessThanOrEqual(1)

      const axe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
      const blockingViolations = axe.violations.filter(
        (violation) => violation.impact === 'serious' || violation.impact === 'critical',
      )
      expect(blockingViolations, `${viewport.name} has blocking accessibility violations`).toEqual([])

      await page.screenshot({
        path: testInfo.outputPath(`login-${viewport.name}.png`),
        fullPage: true,
      })
    }

    const health = await page.evaluate(async () => {
      const response = await fetch('/api/v1/open/health')
      return {
        status: response.status,
        contentType: response.headers.get('content-type'),
        body: await response.json(),
      }
    })
    expect(health.status).toBe(200)
    expect(health.contentType).toContain('application/json')
    expect(health.body).toMatchObject({
      code: 0,
      data: { status: 'ok' },
    })

    expect(runtimeErrors).toEqual([])
    expect(failedRequests).toEqual([])
  })
})
