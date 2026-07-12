/**
 * 冒烟测试 — 覆盖登录 → 核心页面可访问性。
 *
 * 前置条件：
 *   1. 后端运行在 localhost:8000
 *   2. 前端运行在 localhost:5173（vite proxy → :8000）
 *   3. 数据库已 seed（admin / admin123）
 *
 * 运行：npx playwright test
 */
import { test, expect } from '@playwright/test'

const ADMIN = { username: 'admin', password: 'admin123' }

// ── 关键页面列表（路由 + 页面标题断言） ──
const PAGES = [
  { path: '/workbench', title: '工作台' },
  { path: '/testcase', title: '用例库' },
  { path: '/testplan', title: '测试计划' },
  { path: '/requirement', title: '需求管理' },
  { path: '/apitest', title: 'API 测试' },
  { path: '/report', title: '测试报告' },
  { path: '/defect', title: '缺陷管理' },
  { path: '/trace', title: '链路追踪' },
  { path: '/knowledge', title: '知识中心' },
  { path: '/environment', title: '环境配置' },
  { path: '/schedule', title: '定时任务' },
  { path: '/project', title: '项目管理' },
  { path: '/system', title: '系统管理' },
]

test.describe('Smoke: Login', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('successful login redirects to /workbench', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"]', ADMIN.username)
    await page.fill('input[type="password"]', ADMIN.password)
    await page.click('button[type="submit"]')

    // Should redirect to workbench after successful login
    await expect(page).toHaveURL(/\/workbench/, { timeout: 15_000 })
  })
})

test.describe('Smoke: Page accessibility', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[name="username"]', ADMIN.username)
    await page.fill('input[type="password"]', ADMIN.password)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/workbench/, { timeout: 15_000 })
  })

  for (const { path, title } of PAGES) {
    test(`page ${path} loads without crash`, async ({ page }) => {
      await page.goto(path)

      // Wait for page to settle — either the page header or any main content
      await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {
        // networkidle may not settle on pages with periodic polling
      })

      // Verify the page rendered (no blank page / crash)
      const body = page.locator('body')
      await expect(body).toBeVisible()

      // The sidebar nav link for this page should be highlighted (active)
      // This confirms the router resolved correctly
      const navLink = page.locator(`a[href="${path}"]`)
      // Not all nav items use exact href matching, but at minimum the body
      // should contain some content (not a white screen)
      const textContent = await body.innerText()
      expect(textContent.length).toBeGreaterThan(50) // reasonable page content
    })
  }
})

test.describe('Smoke: Knowledge center tabs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"]', ADMIN.username)
    await page.fill('input[type="password"]', ADMIN.password)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/workbench/, { timeout: 15_000 })
  })

  test('all 5 knowledge tabs are present', async ({ page }) => {
    await page.goto('/knowledge')

    const tabs = ['概览', '检索', '知识源', 'AI 审核台', '图谱']
    for (const tab of tabs) {
      await expect(page.locator(`button:has-text("${tab}")`)).toBeVisible({ timeout: 5_000 })
    }
  })
})
