import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Page, type Route } from '@playwright/test'

const THEMES = ['cyberpunk', 'apple', 'clay', 'xlab', 'liquid-glass'] as const
const MODES = ['light', 'dark'] as const
const VIEWPORTS = [
  { id: 'mobile', width: 390, height: 844, hasTouch: true },
  { id: 'tablet', width: 768, height: 1024, hasTouch: true },
  { id: 'desktop', width: 1440, height: 900, hasTouch: false },
] as const
const SURFACES = [
  { path: '/workbench', heading: '工作台' },
  { path: '/testcase', heading: '用例服务' },
  { path: '/integration', heading: '集成配置' },
  { path: '/knowledge?tab=graph', heading: '知识中心' },
] as const

const TEST_CASES = Array.from({ length: 100 }, (_, index) => ({
  id: index + 1,
  module: index % 2 === 0 ? '主题治理' : '共享组件',
  title: index === 0
    ? '超长标题：五主题在移动端、平板与桌面端均保持可读、可操作并通过生产门禁'
    : `Batch 54 生产用例 ${String(index + 1).padStart(3, '0')}`,
  priority: `P${index % 4}`,
  preconditions: ['已登录', '已选择 Batch 54 项目'],
  steps: [{ step: 1, action: '执行核心操作', expected: '主题和组件状态正确' }],
  expected_result: '布局、交互、主题与接口数据一致',
  review_status: ['draft', 'submitted', 'approved', 'rejected'][index % 4],
  created_at: `2026-07-${String(28 - (index % 20)).padStart(2, '0')}T08:00:00Z`,
}))

const DASHBOARD_STATS = {
  total_cases: 128,
  total_plans: 12,
  api_cases: 86,
  pass_rate: 96.8,
  case_type_stats: [
    { case_type: 'manual', label: '功能用例', count: 72, execution_pass: 66, execution_fail: 6, pass_rate: 91.7, fail_rate: 8.3 },
    { case_type: 'api', label: '接口用例', count: 56, execution_pass: 54, execution_fail: 2, pass_rate: 96.4, fail_rate: 3.6 },
  ],
  priority_distribution: [
    { case_type: 'manual', label: '功能用例', color: '#35e68a', total: 72, p0: 8, p1: 24, p2: 30, p3: 10 },
    { case_type: 'api', label: '接口用例', color: '#65a9ff', total: 56, p0: 6, p1: 18, p2: 22, p3: 10 },
  ],
  time_range: { start: '2026-07-21', end: '2026-07-28' },
}

const CROSS_PROJECT_STATS = {
  projects: [{ id: 54, code: 'batch54', name: 'Batch 54 五主题验收项目' }],
  aggregate: { total_projects: 1, total_cases: 128, total_plans: 12, total_api_cases: 86, overall_pass_rate: 96.8, total_defects: 3 },
  per_project: [{ project_id: 54, project_name: 'Batch 54 五主题验收项目', total_cases: 128, total_plans: 12, api_cases: 86, pass_rate: 96.8, defect_count: 3 }],
  trends: {
    pass_rate: [{ date: '2026-07-28', pass_rate: 96.8, total_execs: 104 }],
    defects: [{ date: '2026-07-28', count: 3 }],
  },
}

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

async function installProductionFixture(page: Page, theme: string, mode: string) {
  await page.emulateMedia({ colorScheme: mode as 'light' | 'dark', reducedMotion: 'reduce' })
  await page.addInitScript(({ selectedTheme, selectedMode }) => {
    localStorage.setItem('cameltv-theme-color', selectedTheme)
    localStorage.setItem('cameltv-theme-mode', selectedMode)
    localStorage.setItem(
      'cameltv-auth',
      JSON.stringify({
        state: {
          user: { id: 54, username: 'batch54-ui', nickname: 'Batch 54 UI' },
          projects: [{ id: 54, code: 'batch54', name: 'Batch 54 五主题验收项目' }],
          permissions: ['*'],
          currentProjectId: 54,
          projectThemeMap: {},
        },
        version: 0,
      }),
    )
  }, { selectedTheme: theme, selectedMode: mode })

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const apiPath = url.pathname.replace(/^\/api\/v1/, '')
    if (apiPath === '/system/menus') {
      return ok(route, [
        { id: 1, code: 'menu:workbench', name: '工作台', path: '/workbench', icon: 'DashboardOutlined', sort: 1 },
        { id: 2, code: 'menu:testcase', name: '用例服务', path: '/testcase', icon: 'ProfileOutlined', sort: 2 },
        { id: 3, code: 'menu:integration', name: '集成配置', path: '/integration', icon: 'ApiOutlined', sort: 3 },
        { id: 4, code: 'menu:knowledge', name: '知识中心', path: '/knowledge', icon: 'BookOutlined', sort: 4 },
      ])
    }
    if (apiPath === '/dashboard/stats') return ok(route, DASHBOARD_STATS)
    if (apiPath === '/dashboard/cross-project') return ok(route, CROSS_PROJECT_STATS)
    if (apiPath === '/test-cases/domains') {
      return ok(route, [{ domain: 'Batch 54', count: TEST_CASES.length, modules: [{ module: '主题治理', count: 50 }, { module: '共享组件', count: 50 }] }])
    }
    if (apiPath === '/test-cases') {
      const pageNumber = Number(url.searchParams.get('page') || 1)
      const pageSize = Number(url.searchParams.get('page_size') || 20)
      const start = (pageNumber - 1) * pageSize
      return ok(route, { total: TEST_CASES.length, page: pageNumber, page_size: pageSize, items: TEST_CASES.slice(start, start + pageSize) })
    }
    if (apiPath === '/integrations') return ok(route, { items: [], total: 0 })
    if (apiPath === '/requirements') return ok(route, { items: [], total: 0, page: 1, page_size: 20 })
    if (apiPath === '/knowledge/graph/view') {
      return ok(route, {
        nodes: [
          { id: 'theme:54', entity_type: 'theme', name: '五主题生产治理', group: 'theme', confidence: 1, entity_id: 54 },
          { id: 'component:shared', entity_type: 'component', name: '共享组件契约', group: 'component', confidence: 0.98, entity_id: 55 },
        ],
        edges: [{ source: 'theme:54', target: 'component:shared', relation_type: 'governs', confidence: 0.99 }],
      })
    }
    if (request.method() !== 'GET') return route.abort('blockedbyclient')
    return ok(route, [])
  })
}

function monitorRuntime(page: Page) {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('requestfailed', (request) => {
    errors.push(`requestfailed: ${request.method()} ${request.url()} ${request.failure()?.errorText}`)
  })
  return errors
}

async function assertSurface(page: Page, heading: string, hasTouch: boolean) {
  await expect(page.getByRole('heading', { name: heading, level: 1 })).toBeVisible()
  await page.waitForLoadState('networkidle')
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow, `${heading} 页面级横向溢出`).toBeLessThanOrEqual(1)

  if (hasTouch) {
    const undersized = await page.locator(
      'main button:visible, main a[href]:visible, main input:visible, main select:visible, main textarea:visible, main [role="tab"]:visible, main [role="checkbox"]:visible, main [role="combobox"]:visible, main [role="menuitem"]:visible',
    ).evaluateAll((elements) => elements
      .filter((element) => !element.hasAttribute('disabled'))
      .map((element) => {
        const rect = element.getBoundingClientRect()
        return { label: element.getAttribute('aria-label') || element.textContent?.trim(), width: Math.round(rect.width), height: Math.round(rect.height) }
      })
      .filter((target) => target.width < 44 || target.height < 44))
    expect(undersized, `${heading} 触控目标小于 44×44px`).toEqual([])
  }

  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(axe.violations.map(({ id, nodes }) => ({ id, targets: nodes.map((node) => node.target) })), `${heading} WCAG A/AA 违规`).toEqual([])
}

async function closeContext(context: BrowserContext) {
  await context.close()
}

for (const theme of THEMES) {
  for (const mode of MODES) {
    for (const viewport of VIEWPORTS) {
      test(`${theme} ${mode} ${viewport.id} 五个关键表面满足生产主题门禁`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
          hasTouch: viewport.hasTouch,
          isMobile: viewport.id === 'mobile',
        })
        const page = await context.newPage()
        const runtimeErrors = monitorRuntime(page)

        try {
          await installProductionFixture(page, theme, mode)
          for (const surface of SURFACES) {
            await page.goto(surface.path)
            await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
            await expect(page.locator('html')).toHaveClass(new RegExp(`\\b${mode}\\b`))
            await assertSurface(page, surface.heading, viewport.hasTouch)
          }

          await page.goto('/theme-lab')
          await page.waitForLoadState('networkidle')
          expect(runtimeErrors, 'Theme Lab 运行时错误').toEqual([])
          await expect(page.locator('#theme-lab-workspace')).toBeVisible()
          await expect(page.locator('.theme-lab')).toHaveAttribute('data-theme', theme)
          if (viewport.hasTouch) {
            const undersizedLabTargets = await page.locator(
              '.theme-lab button:visible, .theme-lab input:visible, .theme-lab select:visible, .theme-lab [role="tab"]:visible',
            ).evaluateAll((elements) => elements
              .filter((element) => !element.hasAttribute('disabled'))
              .map((element) => {
                const rect = element.getBoundingClientRect()
                return { label: element.getAttribute('aria-label') || element.textContent?.trim(), width: Math.round(rect.width), height: Math.round(rect.height) }
              })
              .filter((target) => target.width < 44 || target.height < 44))
            expect(undersizedLabTargets, 'Theme Lab 触控目标小于 44×44px').toEqual([])
          }
          const labOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
          const overflowSources = labOverflow > 1
            ? await page.locator('body *').evaluateAll((elements) => elements.flatMap((element) => {
                const rect = element.getBoundingClientRect()
                return rect.right > document.documentElement.clientWidth + 1 || rect.left < -1
                  ? [{ tag: element.tagName, className: element.className, left: Math.round(rect.left), right: Math.round(rect.right), width: Math.round(rect.width) }]
                  : []
              }).slice(0, 12))
            : []
          const layoutDiagnostics = labOverflow > 1
            ? await page.locator('.lab-workspace, .overview-layout, .run-table-panel, .data-table-wrap').evaluateAll((elements) => elements.map((element) => {
                const rect = element.getBoundingClientRect()
                return {
                  className: element.className,
                  left: Math.round(rect.left),
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                  clientWidth: element.clientWidth,
                  scrollWidth: element.scrollWidth,
                  overflowX: getComputedStyle(element).overflowX,
                }
              }))
            : []
          expect(labOverflow, `Theme Lab 页面级横向溢出: ${JSON.stringify({ overflowSources, layoutDiagnostics })}`).toBeLessThanOrEqual(1)
          const labAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
          expect(labAxe.violations.map(({ id, nodes }) => ({
            id,
            targets: nodes.map((node) => ({ target: node.target, detail: node.any[0]?.data })),
          })), 'Theme Lab WCAG A/AA 违规').toEqual([])
          expect(runtimeErrors, '运行时错误').toEqual([])
        } finally {
          await closeContext(context)
        }
      })
    }
  }
}

for (const theme of THEMES) {
  test(`${theme} 在 200% 文本和移动横屏下保持主任务可达`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 844, height: 390 }, hasTouch: true })
    const page = await context.newPage()
    try {
      await installProductionFixture(page, theme, 'light')
      await page.addInitScript(() => { document.documentElement.style.fontSize = '200%' })
      await page.goto('/testcase')
      await expect(page.getByRole('heading', { name: '用例服务', level: 1 })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1)
      const tableRegion = page.getByRole('region', { name: '测试用例数据表' })
      await expect(tableRegion).toBeVisible()
      await expect(page.getByText('共 100 条')).toBeVisible()
      expect(await tableRegion.locator('tbody tr').count()).toBe(20)
      expect(await tableRegion.evaluate((element) => ({
        overflowX: getComputedStyle(element).overflowX,
        tabIndex: element.tabIndex,
      }))).toEqual({ overflowX: 'auto', tabIndex: 0 })
      await page.getByRole('button', { name: '下一页' }).click()
      await expect(tableRegion.getByText('Batch 54 生产用例 021')).toBeVisible()

      await page.goto('/theme-lab')
      const runTrigger = page.getByRole('button', { name: '启动回归' })
      await runTrigger.focus()
      await page.keyboard.press('Enter')
      const dialog = page.getByRole('dialog', { name: '启动回归确认' })
      await expect(dialog).toBeVisible()
      expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
      await page.keyboard.press('Escape')
      await expect(dialog).toBeHidden()
      await expect(runTrigger).toBeFocused()
      await expect(page.locator('.status-pill').filter({ hasText: '失败' }).first()).toBeVisible()
      await expect(page.getByRole('img', { name: /当前回归批次进度/ })).toBeVisible()
    } finally {
      await closeContext(context)
    }
  })
}
