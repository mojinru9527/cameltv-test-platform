import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const username = process.env.E2E_USERNAME || ''
const password = process.env.E2E_PASSWORD || ''
const hasCredentials = Boolean(username && password)

test.describe('Batch 53 real-backend production acceptance', () => {
  test('login, populated testcase and dashboard use the running backend without route mocks', async ({ page }) => {
    test.skip(!hasCredentials, '需要通过环境变量注入隔离的本地 E2E 账号')
    test.setTimeout(90_000)

    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
    await page.addInitScript(() => {
      localStorage.setItem('cameltv-theme-mode', 'dark')
      localStorage.setItem('cameltv-theme-color', 'obsidian-flow')
    })

    const businessRequests: string[] = []
    const consoleErrors: string[] = []
    const pageErrors: string[] = []
    const failedRequests: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/')) businessRequests.push(request.url())
    })
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text())
    })
    page.on('pageerror', (error) => pageErrors.push(error.message))
    page.on('requestfailed', (request) => failedRequests.push(request.url()))

    await page.goto('/login')
    const loginResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/auth/login')
        && response.request().method() === 'POST',
    )
    await page.fill('input[name="username"]', username)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')

    const loginResponse = await loginResponsePromise
    expect(loginResponse.ok()).toBe(true)
    const loginBody = await loginResponse.json()
    const projectId = Number(loginBody?.data?.projects?.[0]?.id)
    expect(projectId).toBeGreaterThan(0)
    await expect(page).toHaveURL(/\/workbench/, { timeout: 15_000 })

    const prefix = `B53-REAL-${Date.now()}`
    const createdIds = await page.evaluate(async ({ projectId, prefix }) => {
      const ids: number[] = []
      for (let index = 0; index < 24; index += 1) {
        const response = await fetch('/api/v1/test-cases', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Project-Id': String(projectId),
          },
          body: JSON.stringify({
            case_id: `${prefix}-${String(index + 1).padStart(2, '0')}`,
            title:
              index === 0
                ? `${prefix} 生产数据移动端长标题与完整交互验收`
                : `${prefix} 真实后端用例 ${String(index + 1).padStart(2, '0')}`,
            domain: 'Batch 53 生产验收',
            module: index % 2 === 0 ? '响应式与可访问性' : '数据一致性',
            case_type: 'manual',
            priority: `P${index % 4}`,
            status: 'active',
            preconditions: '["已登录真实后端","已选择隔离验收项目"]',
            steps: JSON.stringify([
              { step: 1, action: '进入用例服务', expected: '真实数据成功加载' },
              { step: 2, action: '检查筛选和表格', expected: '界面与接口数据一致' },
            ]),
            expected_result: '核心页面在生产数据量下保持可理解、可操作且无溢出',
            source: 'batch53-e2e',
          }),
        })
        const body = await response.json()
        if (!response.ok || body?.code !== 0 || !body?.data?.id) {
          throw new Error(body?.msg || `创建真实用例失败：HTTP ${response.status}`)
        }
        ids.push(Number(body.data.id))
      }
      return ids
    }, { projectId, prefix })

    try {
      await page.setViewportSize({ width: 390, height: 844 })
      const testcaseResponsePromise = page.waitForResponse(
        (response) =>
          response.url().includes('/api/v1/test-cases?')
          && response.request().method() === 'GET',
      )
      await page.goto('/testcase')
      const testcaseResponse = await testcaseResponsePromise
      expect(testcaseResponse.ok()).toBe(true)

      const tableRegion = page.getByRole('region', { name: '测试用例数据表' })
      await expect(tableRegion).toBeVisible()
      await expect(tableRegion.getByText(`${prefix} 生产数据移动端长标题与完整交互验收`)).toBeVisible()
      expect(await tableRegion.locator('tbody tr').count()).toBe(20)
      const tableScroller = tableRegion.locator('[data-slot="table-container"]')
      expect(await tableScroller.evaluate((node) => node.scrollWidth > node.clientWidth)).toBe(true)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)

      const accessibility = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
      expect(accessibility.violations).toEqual([])

      await page.setViewportSize({ width: 1440, height: 900 })
      const dashboardResponsePromise = page.waitForResponse(
        (response) =>
          response.url().includes('/api/v1/dashboard/stats')
          && response.request().method() === 'GET',
      )
      await page.goto('/workbench')
      const dashboardResponse = await dashboardResponsePromise
      expect(dashboardResponse.ok()).toBe(true)
      await expect(page.getByRole('figure', { name: /项目概览/ })).toBeVisible()
      await expect(page.getByRole('table', { name: '项目概览数据' })).toContainText('功能用例')

      expect(businessRequests.some((url) => url.includes('/api/v1/auth/login'))).toBe(true)
      expect(businessRequests.some((url) => url.includes('/api/v1/test-cases'))).toBe(true)
      expect(businessRequests.some((url) => url.includes('/api/v1/dashboard/stats'))).toBe(true)
      expect(consoleErrors).toEqual([])
      expect(pageErrors).toEqual([])
      expect(failedRequests).toEqual([])
    } finally {
      const cleanup = await page.evaluate(async ({ projectId, ids }) => {
        if (ids.length === 0) return
        const response = await fetch('/api/v1/test-cases/batch-delete', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Project-Id': String(projectId),
          },
          body: JSON.stringify({ ids }),
        })
        return { ok: response.ok, status: response.status, body: await response.json() }
      }, { projectId, ids: createdIds })
      expect(cleanup?.ok).toBe(true)
      expect(cleanup?.body?.code).toBe(0)
      expect(cleanup?.body?.data?.deleted).toBe(createdIds.length)
    }
  })
})
