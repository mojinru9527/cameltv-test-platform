/**
 * Batch 89 — C55-5-P2 响应式回归（tablet 768×1024 / mobile 390×844）
 *
 * 契约（Design Spec §1）：
 * - 无水平溢出：documentElement.scrollWidth <= innerWidth + 1
 * - 主操作可点：页面首个按钮可见且可用；登录后可进入各业务页
 * - console error = 0
 * - 每页截图存 evidence/batch-89/responsive/
 *
 * 前置：后端(8046) + 前端(5216) 已启动；凭据经 E2E_USERNAME / E2E_PASSWORD 注入。
 */
import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://localhost:5216'
const USERNAME = process.env.E2E_USERNAME || 'tester'
const PASSWORD = process.env.E2E_PASSWORD || ''
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = path.resolve(SPEC_DIR, '../../work-logs/evidence/batch-89/responsive')

const PAGES = [
  { name: 'workbench', path: '/workbench' },
  { name: 'testcase', path: '/testcase' },
  // (batch-212) '/testplan' 已重定向 /testcase
  { name: 'report', path: '/report' },
  { name: 'defect', path: '/defect' },
  { name: 'schedule', path: '/schedule' },
  { name: 'knowledge', path: '/knowledge' },
]

const VIEWPORTS = [
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
]

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByPlaceholder('用户名').fill(USERNAME)
  await page.getByPlaceholder('密码').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 20_000 })
  await page.waitForLoadState('networkidle')
}

async function assertNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }))
  expect(
    metrics.scrollWidth,
    `水平溢出: scrollWidth=${metrics.scrollWidth} > innerWidth=${metrics.innerWidth}`,
  ).toBeLessThanOrEqual(metrics.innerWidth + 1)
}

for (const vp of VIEWPORTS) {
  test.describe(`C55-5-P2 ${vp.name} ${vp.width}x${vp.height}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } })

    test('登录 + 关键业务页无水平溢出、主操作可点', async ({ page }) => {
      const consoleErrors: string[] = []
      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text())
      })

      // 登录页本身
      await page.goto(`${BASE_URL}/login`)
      await page.waitForLoadState('networkidle')
      await assertNoHorizontalOverflow(page)
      await page.screenshot({
        path: path.join(EVIDENCE_DIR, `${vp.name}-login.png`),
        fullPage: true,
      })

      await login(page)

      for (const p of PAGES) {
        await page.goto(`${BASE_URL}${p.path}`)
        await page.waitForLoadState('networkidle')
        await assertNoHorizontalOverflow(page)

        // 主操作抽查：页面首个可见按钮可点击（空态/工具条）
        const firstButton = page.locator('button:visible').first()
        if (await firstButton.count()) {
          await expect(firstButton).toBeEnabled()
        }
        await page.screenshot({
          path: path.join(EVIDENCE_DIR, `${vp.name}-${p.name}.png`),
          fullPage: true,
        })
      }

      // 移动端：侧边栏开合抽查（SidebarTrigger 存在则点击并断言菜单可见）
      if (vp.name === 'mobile') {
        const trigger = page.getByLabel('Toggle Sidebar')
        if (await trigger.count()) {
          await trigger.first().click()
          await expect(page.locator('nav').first()).toBeVisible({ timeout: 5000 })
        }
      }

      expect(consoleErrors, `console errors: ${consoleErrors.join(' | ')}`).toEqual([])
    })
  })
}
