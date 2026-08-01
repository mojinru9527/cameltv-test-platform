import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type Route } from '@playwright/test'

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
] as const

const SURFACES = [
  { path: '/login', heading: 'CamelTv 测试平台', authenticated: false },
  { path: '/apitest', heading: '接口测试', authenticated: true },
  { path: '/uitest', heading: 'UI 测试', authenticated: true },
  { path: '/report', heading: '报告中心', authenticated: true },
  { path: '/schedule', heading: '定时任务', authenticated: true },
  { path: '/notify', heading: '通知配置', authenticated: true },
  { path: '/release-bundles', heading: '版本发布包', authenticated: true },
] as const

const EMPTY_PAGE = { total: 0, page: 1, page_size: 20, items: [] }

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

function responseFor(path: string) {
  if (path === '/system/menus') return []
  if (path === '/apitest/services') return []
  if (path === '/apitest/endpoints') return EMPTY_PAGE
  if (path === '/ui-tests') return EMPTY_PAGE
  if (path === '/ui-tests/scripts') return { available_specs: [] }
  if (path === '/environments') return []
  if (path === '/reports') return EMPTY_PAGE
  if (path === '/reports/trends') {
    return {
      points: [],
      summary: {
        total_reports: 0,
        avg_pass_rate: 0,
        best_pass_rate: 0,
        worst_pass_rate: 0,
        latest_open_defects: 0,
      },
    }
  }
  if (path === '/schedules') return EMPTY_PAGE
  if (path === '/test-plans') return EMPTY_PAGE
  if (path === '/notify/channels') return []
  if (path === '/release-bundles') return { ...EMPTY_PAGE, page_size: 200 }
  return []
}

async function installFixture(page: Page, authenticated: boolean) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  if (authenticated) {
    await page.addInitScript(() => {
      localStorage.setItem('cameltv-auth', JSON.stringify({
        state: {
          user: { id: 61, username: 'a11y-admin', nickname: 'A11y Admin', email: '' },
          projects: [{ id: 61, code: 'batch61', name: 'Batch 61 A11y 项目' }],
          permissions: ['*'],
          currentProjectId: 61,
          mustChangePassword: false,
          projectThemeMap: {},
        },
        version: 0,
      }))
    })
  }
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() !== 'GET') return ok(route, null)
    return ok(route, responseFor(path))
  })
}

test.describe('Batch 61 keyboard, responsive and axe baseline', () => {
  for (const surface of SURFACES) {
    for (const viewport of VIEWPORTS) {
      test(`${surface.path} ${viewport.name}`, async ({ page }) => {
        await installFixture(page, surface.authenticated)
        await page.setViewportSize(viewport)
        await page.goto(surface.path)
        await expect(page.getByRole('heading', { level: 1, name: surface.heading })).toBeVisible()

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        )
        expect(overflow, 'global viewport overflow').toBeLessThanOrEqual(1)

        await page.keyboard.press('Tab')
        const focused = await page.evaluate(() => ({
          tag: document.activeElement?.tagName,
          name: document.activeElement?.getAttribute('aria-label')
            || document.activeElement?.getAttribute('name')
            || document.activeElement?.textContent?.trim(),
        }))
        expect(focused.tag).not.toBe('BODY')
        expect(focused.name).toBeTruthy()

        const axe = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()
        expect(axe.violations.map(({ id, nodes }) => ({
          id,
          targets: nodes.map((node) => node.target),
        }))).toEqual([])
      })
    }
  }
})
