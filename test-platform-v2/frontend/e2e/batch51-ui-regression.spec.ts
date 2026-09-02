import AxeBuilder from '@axe-core/playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { expect, test, type Page, type Route, type TestInfo } from '@playwright/test'

type PageSpec = {
  id: string
  path: string
  heading: string
  ownsTheme?: boolean
}

type RuntimeSignals = {
  consoleErrors: string[]
  pageErrors: string[]
  failedRequests: string[]
}

const VIEWPORTS = [
  { id: 'desktop', width: 1440, height: 900, axe: true },
  { id: 'tablet', width: 768, height: 1024, axe: false },
  { id: 'mobile', width: 390, height: 844, axe: false },
] as const

const CORE_PAGES: PageSpec[] = [
  { id: 'environment', path: '/environment', heading: '环境与变量管理' },
  { id: 'defect', path: '/defect', heading: '缺陷管理' },
  { id: 'testcase', path: '/testcase', heading: '用例服务' },
  // (batch-212) '/testplan' 已重定向 /testcase
  { id: 'report', path: '/report', heading: '报告中心' },
  { id: 'trace', path: '/trace', heading: '质量追溯' },
  { id: 'requirement', path: '/requirement', heading: '需求文档' },
]

const SCREENSHOT_PAGES: PageSpec[] = [
  { id: 'workbench', path: '/workbench', heading: '工作台' },
  { id: 'trace', path: '/trace', heading: '质量追溯' },
  { id: 'testcase', path: '/testcase', heading: '用例服务' },
  { id: 'environment', path: '/environment', heading: '环境与变量管理' },
  {
    id: 'theme-lab',
    path: '/theme-lab',
    heading: '把测试从页面集合，变成一条可操作的质量链。',
    ownsTheme: true,
  },
]

const EMPTY_PAGE = { total: 0, page: 1, page_size: 20, items: [] }

const API_RESPONSES: Record<string, unknown> = {
  '/system/menus': [
    { id: 1, code: 'menu:workbench', name: '工作台', path: '/workbench', icon: 'DashboardOutlined', sort: 1 },
    { id: 2, code: 'menu:trace', name: '质量追溯', path: '/trace', icon: 'NodeIndexOutlined', sort: 2 },
    { id: 3, code: 'menu:requirement', name: '需求文档', path: '/requirement', icon: 'FileTextOutlined', sort: 3 },
    { id: 4, code: 'menu:testcase', name: '用例服务', path: '/testcase', icon: 'ProfileOutlined', sort: 4 },
    // (batch-212) menu:testplan 已下架
    { id: 6, code: 'menu:report', name: '报告中心', path: '/report', icon: 'BarChartOutlined', sort: 6 },
  ],
  '/environments': [],
  '/defects': EMPTY_PAGE,
  '/defects/stats': { total: 0, by_severity: {}, by_status: {} },
  '/test-cases': EMPTY_PAGE,
  '/test-cases/domains': [],
  '/test-plans': EMPTY_PAGE,
  '/reports': EMPTY_PAGE,
  '/reports/trends': {
    points: [],
    summary: {
      total_reports: 0,
      avg_pass_rate: 0,
      best_pass_rate: 0,
      worst_pass_rate: 0,
      latest_open_defects: 0,
    },
  },
  '/trace/coverage': {
    total_cases: 0,
    cases_in_plans: 0,
    cases_executed: 0,
    cases_passed: 0,
    cases_with_defects: 0,
    by_type: {},
    by_domain: {},
    coverage_rate: 0,
    execution_rate: 0,
    pass_rate: 0,
    requirement_count: 0,
    requirements_with_cases: 0,
    requirement_coverage_rate: 0,
  },
  '/requirements': { ...EMPTY_PAGE, page_size: 10 },
  '/lanhu-evidence/jobs': { ...EMPTY_PAGE, page_size: 50 },
  '/dashboard/stats': {
    total_cases: 0,
    total_plans: 0,
    api_cases: 0,
    pass_rate: 0,
    case_type_stats: [],
    priority_distribution: [],
    time_range: null,
  },
}

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

async function installBrowserFixtures(page: Page) {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    localStorage.setItem('cameltv-auth', JSON.stringify({
      state: {
        user: {
          id: 51,
          username: 'batch51-ui',
          nickname: 'Batch 51 UI',
          email: 'batch51-ui@example.invalid',
        },
        projects: [{ id: 51, code: 'batch51', name: 'Batch 51 UI 验收项目' }],
        permissions: ['*'],
        currentProjectId: 51,
        projectThemeMap: {},
      },
      version: 0,
    }))
    localStorage.setItem('cameltv-theme-mode', 'dark')
    localStorage.setItem('cameltv-theme-color', 'obsidian-flow')
  })

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const apiPath = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'GET' && Object.hasOwn(API_RESPONSES, apiPath)) {
      return ok(route, API_RESPONSES[apiPath])
    }
    return route.abort('blockedbyclient')
  })
}

function observeRuntime(page: Page): RuntimeSignals {
  const signals: RuntimeSignals = {
    consoleErrors: [],
    pageErrors: [],
    failedRequests: [],
  }
  page.on('console', (message) => {
    if (message.type() === 'error') signals.consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => signals.pageErrors.push(error.message))
  page.on('requestfailed', (request) => {
    signals.failedRequests.push(
      `${request.method()} ${request.url()} — ${request.failure()?.errorText || 'unknown error'}`,
    )
  })
  return signals
}

async function openStablePage(page: Page, spec: PageSpec) {
  await page.goto(spec.path)
  const heading = page.getByRole('heading', { level: 1, name: spec.heading, exact: true })
  await expect(heading).toHaveCount(1)
  await expect(heading).toBeVisible()
  if (!spec.ownsTheme) {
    await expect(page.locator('html')).toHaveAttribute('data-ui-theme', 'obsidian-flow')
  }
  await page.waitForLoadState('networkidle')
}

async function expectNoHorizontalOverflow(page: Page, pathName: string) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow, `${pathName} must not create global horizontal overflow`).toBeLessThanOrEqual(1)
}

function expectCleanRuntime(signals: RuntimeSignals) {
  expect(signals.consoleErrors, 'browser console errors').toEqual([])
  expect(signals.pageErrors, 'uncaught page errors').toEqual([])
  expect(signals.failedRequests, 'failed browser requests').toEqual([])
}

function screenshotPath(testInfo: TestInfo, name: string) {
  const evidenceDir = process.env.E2E_EVIDENCE_DIR
  if (!evidenceDir) return testInfo.outputPath(name)
  mkdirSync(evidenceDir, { recursive: true })
  return path.join(evidenceDir, name)
}

test.describe('Batch 51 core page UI contract', () => {
  for (const pageSpec of CORE_PAGES) {
    for (const viewport of VIEWPORTS) {
      test(`${pageSpec.id} ${viewport.id}: one h1, responsive shell and clean runtime`, async ({ page }) => {
        const signals = observeRuntime(page)
        await installBrowserFixtures(page)
        await page.setViewportSize(viewport)
        await openStablePage(page, pageSpec)
        await expectNoHorizontalOverflow(page, pageSpec.path)

        if (viewport.axe) {
          const results = await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
            .analyze()
          expect(
            results.violations.map(({ id, impact, nodes }) => ({
              id,
              impact,
              nodes: nodes.length,
              targets: nodes.slice(0, 5).map((node) => node.target),
            })),
          ).toEqual([])
        }

        expectCleanRuntime(signals)
      })
    }
  }
})

test.describe('Batch 50 visual evidence', () => {
  for (const pageSpec of SCREENSHOT_PAGES) {
    for (const viewport of VIEWPORTS) {
      test(`${pageSpec.id} ${viewport.id}: capture full-page evidence`, async ({ page }, testInfo) => {
        const signals = observeRuntime(page)
        await installBrowserFixtures(page)
        await page.setViewportSize(viewport)
        await openStablePage(page, pageSpec)
        await expectNoHorizontalOverflow(page, pageSpec.path)

        const fileName = `${pageSpec.id}-${viewport.id}-${viewport.width}x${viewport.height}.png`
        await page.screenshot({
          path: screenshotPath(testInfo, fileName),
          fullPage: true,
          animations: 'disabled',
          caret: 'hide',
        })

        expectCleanRuntime(signals)
      })
    }
  }
})
