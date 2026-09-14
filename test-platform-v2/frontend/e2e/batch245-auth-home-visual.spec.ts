import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type Route } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 812 },
] as const

const PUBLIC_ACCESS = {
  registration_enabled: true,
  invite_code_required: false,
  password_reset_email_enabled: false,
  modules: [
    {
      code: 'quality',
      name: '质量管理',
      path: '/quality',
      icon: '',
      sort: 1,
      children: [
        { code: 'testcase', name: '用例服务', path: '/testcase', icon: '', sort: 1 },
        { code: 'report', name: '报告中心', path: '/report', icon: '', sort: 2 },
      ],
    },
  ],
}

const EVIDENCE_DIR = resolve(process.cwd(), '../../work-logs/evidence/batch-245')

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

async function installFixture(page: Page) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/public-access')) return ok(route, PUBLIC_ACCESS)
    if (path.endsWith('/auth/forgot-password')) return ok(route, null)
    return ok(route, null)
  })
}

async function expectNoOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow, 'viewport overflow').toBeLessThanOrEqual(1)
}

async function expectAxeClean(page: Page) {
  const axe = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(axe.violations.map(({ id, nodes }) => ({
    id,
    targets: nodes.map((node) => node.target),
  }))).toEqual([])
}

test.describe('Batch 245 task-first home and password recovery', () => {
  for (const viewport of VIEWPORTS) {
    test(`home ${viewport.name}`, async ({ page }, testInfo) => {
      mkdirSync(EVIDENCE_DIR, { recursive: true })
      await installFixture(page)
      await page.setViewportSize(viewport)
      await page.goto('/')

      await expect(page.getByRole('heading', { name: '从测试任务开始，而不是先找模块' })).toBeVisible()
      await expect(page.locator('button[aria-label^="登录后"]')).toHaveCount(4)
      await page.getByRole('button', { name: /展开模块/ }).click()
      await expect(page.getByText('用例服务')).toBeVisible()
      await expectNoOverflow(page)
      await expectAxeClean(page)

      const screenshotPath = resolve(EVIDENCE_DIR, `home-${viewport.name}.png`)
      await page.screenshot({ path: screenshotPath, fullPage: true })
      await testInfo.attach(`home-${viewport.name}`, {
        path: screenshotPath,
        contentType: 'image/png',
      })
    })
  }

  for (const viewport of VIEWPORTS) {
    test(`password recovery ${viewport.name}`, async ({ page }, testInfo) => {
      mkdirSync(EVIDENCE_DIR, { recursive: true })
      await installFixture(page)
      await page.setViewportSize(viewport)
      await page.goto('/login')

      await expect(page.getByRole('heading', { name: 'CamelTv 测试平台' })).toBeVisible()
      await expect(page.getByRole('link', { name: '忘记密码？' })).toBeVisible()
      await page.getByRole('link', { name: '忘记密码？' }).click()
      await expect(page.getByRole('heading', { name: '找回密码' })).toBeVisible()
      await page.getByLabel('用户名').fill('visual-check')
      await page.getByRole('button', { name: '发送重置链接' }).click()
      await expect(page.getByText('请求已提交')).toBeVisible()
      await expectNoOverflow(page)
      await expectAxeClean(page)

      const screenshotPath = resolve(EVIDENCE_DIR, `forgot-password-${viewport.name}.png`)
      await page.screenshot({ path: screenshotPath, fullPage: true })
      await testInfo.attach(`forgot-password-${viewport.name}`, {
        path: screenshotPath,
        contentType: 'image/png',
      })
    })
  }
})
