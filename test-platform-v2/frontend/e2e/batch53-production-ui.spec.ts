import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type Route } from '@playwright/test'

const VIEWPORTS = [
  { id: 'mobile', width: 390, height: 844 },
  { id: 'tablet', width: 768, height: 1024 },
  { id: 'desktop', width: 1440, height: 900 },
] as const

const TEST_CASES = Array.from({ length: 24 }, (_, index) => {
  const id = index + 1
  return {
    id,
    module: index % 2 === 0 ? '账号与权限' : '报告与追溯',
    title:
      index === 0
        ? '超长标题：验证生产环境中跨项目权限、分页、筛选与审计结果在移动端仍然完整可理解'
        : `生产级测试用例 ${String(id).padStart(2, '0')}`,
    priority: `P${index % 4}`,
    preconditions: ['已登录', '已选择 Batch 53 项目'],
    steps: [
      { step: 1, action: '打开目标页面', expected: '页面加载成功' },
      { step: 2, action: '执行核心操作', expected: '结果与接口一致' },
    ],
    expected_result: '操作成功且数据一致',
    review_status: ['draft', 'submitted', 'approved', 'rejected'][index % 4],
    created_at: `2026-07-${String(28 - (index % 20)).padStart(2, '0')}T08:00:00Z`,
  }
})

const DASHBOARD_STATS = {
  total_cases: 128,
  total_plans: 12,
  api_cases: 86,
  pass_rate: 96.8,
  case_type_stats: [
    {
      case_type: 'manual',
      label: '功能用例',
      count: 72,
      execution_pass: 66,
      execution_fail: 6,
      pass_rate: 91.7,
      fail_rate: 8.3,
    },
    {
      case_type: 'api',
      label: '接口用例',
      count: 56,
      execution_pass: 54,
      execution_fail: 2,
      pass_rate: 96.4,
      fail_rate: 3.6,
    },
  ],
  priority_distribution: [
    {
      case_type: 'manual',
      label: '功能用例',
      color: '#35e68a',
      total: 72,
      p0: 8,
      p1: 24,
      p2: 30,
      p3: 10,
    },
    {
      case_type: 'api',
      label: '接口用例',
      color: '#65a9ff',
      total: 56,
      p0: 6,
      p1: 18,
      p2: 22,
      p3: 10,
    },
  ],
  time_range: { start: '2026-07-21', end: '2026-07-28' },
}

const CROSS_PROJECT_STATS = {
  projects: [
    { id: 53, code: 'batch53', name: 'Batch 53 生产验收项目' },
    { id: 54, code: 'shared', name: '共享质量项目' },
  ],
  aggregate: {
    total_projects: 2,
    total_cases: 248,
    total_plans: 21,
    total_api_cases: 126,
    overall_pass_rate: 95.4,
    total_defects: 8,
  },
  per_project: [
    {
      project_id: 53,
      project_name: 'Batch 53 生产验收项目',
      total_cases: 128,
      total_plans: 12,
      api_cases: 66,
      pass_rate: 96.8,
      defect_count: 3,
    },
    {
      project_id: 54,
      project_name: '共享质量项目',
      total_cases: 120,
      total_plans: 9,
      api_cases: 60,
      pass_rate: 94,
      defect_count: 5,
    },
  ],
  trends: {
    pass_rate: [
      { date: '2026-07-27', pass_rate: 94.2, total_execs: 92 },
      { date: '2026-07-28', pass_rate: 95.4, total_execs: 104 },
    ],
    defects: [
      { date: '2026-07-27', count: 3 },
      { date: '2026-07-28', count: 2 },
    ],
  },
}

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

async function installFixtures(
  page: Page,
  options: {
    menuFailureOnce?: boolean
    dashboardFailureOnce?: boolean
    integrationItem?: boolean
    integrationCreate?: boolean
    slowTestcaseKeyword?: string
  } = {},
) {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    localStorage.setItem(
      'cameltv-auth',
      JSON.stringify({
        state: {
          user: {
            id: 53,
            username: 'batch53-ui',
            nickname: 'Batch 53 UI',
            email: 'batch53-ui@example.invalid',
          },
          projects: [{ id: 53, code: 'batch53', name: 'Batch 53 生产验收项目' }],
          permissions: ['*'],
          currentProjectId: 53,
          projectThemeMap: {},
        },
        version: 0,
      }),
    )
    localStorage.setItem('cameltv-theme-mode', 'dark')
    localStorage.setItem('cameltv-theme-color', 'obsidian-flow')
  })

  let menuAttempts = 0
  let dashboardAttempts = 0
  let integrationDeleted = false
  let integrationCreated = false
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const apiPath = url.pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'DELETE' && apiPath === '/integrations/53') {
      integrationDeleted = true
      return ok(route, { deleted: true })
    }
    if (request.method() === 'POST' && apiPath === '/integrations' && options.integrationCreate) {
      integrationCreated = true
      await new Promise((resolve) => setTimeout(resolve, 250))
      return ok(route, {
        id: 54,
        name: 'Batch 53 新建集成',
        provider_type: 'jira',
        base_url: 'https://jira.example.invalid',
        auth_json: '{}',
        sync_direction: 'bidirectional',
        sync_interval_minutes: 0,
        enabled: true,
      })
    }
    if (request.method() !== 'GET') return route.abort('blockedbyclient')
    if (apiPath === '/system/menus') {
      menuAttempts += 1
      // React StrictMode mounts the effect twice in development; keep both
      // initial attempts failed so the user-visible recovery state is exercised.
      if (options.menuFailureOnce && menuAttempts <= 2) {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, msg: 'menu unavailable', data: null }),
        })
      }
      return ok(route, [
        {
          id: 1,
          code: 'menu:workbench',
          name: '工作台',
          path: '/workbench',
          icon: 'DashboardOutlined',
          sort: 1,
        },
        {
          id: 2,
          code: 'menu:testcase',
          name: '用例服务',
          path: '/testcase',
          icon: 'ProfileOutlined',
          sort: 2,
        },
      ])
    }
    if (apiPath === '/dashboard/stats') {
      dashboardAttempts += 1
      if (options.dashboardFailureOnce && dashboardAttempts === 1) {
        await new Promise((resolve) => setTimeout(resolve, 1200))
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, msg: '统计服务暂时不可用', data: null }),
        })
      }
      return ok(route, DASHBOARD_STATS)
    }
    if (apiPath === '/dashboard/cross-project') return ok(route, CROSS_PROJECT_STATS)
    if (apiPath === '/knowledge/graph/view') {
      return ok(route, {
        nodes: [
          {
            id: 'project:53',
            entity_type: 'project',
            name: 'Batch 53 生产验收',
            group: 'project',
            description: '黑曜玻璃生产级 UI 验收项目',
            confidence: 1,
            entity_id: 53,
          },
          {
            id: 'module:responsive',
            entity_type: 'module',
            name: '响应式与可访问性',
            group: 'module',
            description: '移动端、键盘和读屏兼容',
            confidence: 0.98,
            entity_id: 54,
          },
        ],
        edges: [
          {
            source: 'project:53',
            target: 'module:responsive',
            relation_type: 'contains',
            confidence: 0.99,
          },
        ],
      })
    }
    if (apiPath === '/knowledge/graph/hierarchy') {
      return ok(route, {
        project_id: 53,
        project_name: 'Batch 53 生产验收',
        nodes: [
          {
            id: 'project:53',
            name: 'Batch 53 生产验收',
            node_type: 'project',
            parent_id: null,
            version: '53',
            platform: 'WEB',
            change_type: 'unchanged',
            metadata: { description: '黑曜玻璃主题生产验收' },
          },
          {
            id: 'module:responsive',
            name: '响应式与可访问性',
            node_type: 'module',
            parent_id: 'project:53',
            version: '53',
            platform: 'WEB',
            change_type: 'modified',
            metadata: { description: '移动端、键盘和读屏兼容' },
          },
        ],
        edges: [
          {
            source: 'project:53',
            target: 'module:responsive',
            relation_type: 'contains',
            confidence: 0.99,
            label: '包含',
          },
        ],
        stats: { 项目: 1, 模块: 1 },
      })
    }
    if (apiPath === '/requirement-modules/bundle/53/tree') {
      return ok(route, {
        bundle_id: 53,
        bundle_name: 'Batch 53',
        client_version: '53.0.0',
        admin_version: '53.0.0',
        roots: [{
          id: 5301,
          name: '账号与权限',
          node_type: 'module',
          platform: 'WEB',
          change_type: 'modified',
          description: '账号与权限模块',
          lanhu_page_id: '',
          page_interactions: '[]',
          child_count: 1,
          children: [{
            id: 5302,
            name: '登录页',
            node_type: 'page',
            platform: 'WEB',
            change_type: 'modified',
            description: '登录与错误反馈',
            lanhu_page_id: 'batch53-login',
            page_interactions: JSON.stringify([{
              trigger: '提交登录表单',
              target_page: '工作台',
              interaction_type: 'navigation',
            }]),
            child_count: 0,
            children: [],
          }],
        }],
        total_modules: 1,
        total_pages: 1,
        total_attachments: 0,
      })
    }
    if (apiPath === '/requirement-modules/5302') {
      return ok(route, {
        id: 5302,
        name: '登录页',
        node_type: 'page',
        platform: 'WEB',
        page_interactions: JSON.stringify([{
          trigger: '提交登录表单',
          target_page: '工作台',
          interaction_type: 'navigation',
        }]),
      })
    }
    if (apiPath === '/requirement-modules/bundle/53/admin-links') return ok(route, [])
    if (apiPath === '/requirement-modules/bundle/53/global-nav') return ok(route, [])
    if (apiPath === '/release-bundles') {
      return ok(route, {
        total: 1,
        page: 1,
        page_size: 200,
        items: [{
          id: 53,
          name: 'Batch 53',
          client_version: '53.0.0',
          admin_version: '53.0.0',
          status: 'active',
          module_count: 1,
          page_count: 1,
        }],
      })
    }
    if (apiPath === '/integrations') {
      const items = options.integrationItem && !integrationDeleted
        ? [{
            id: 53,
            name: 'Batch 53 Jira',
            provider_type: 'jira',
            base_url: 'https://jira.example.invalid',
            auth_json: '{}',
            sync_direction: 'bidirectional',
            sync_interval_minutes: 0,
            enabled: true,
          }]
        : integrationCreated
          ? [{
              id: 54,
              name: 'Batch 53 新建集成',
              provider_type: 'jira',
              base_url: 'https://jira.example.invalid',
              auth_json: '{}',
              sync_direction: 'bidirectional',
              sync_interval_minutes: 0,
              enabled: true,
            }]
          : []
      return ok(route, { items, total: items.length })
    }
    if (apiPath === '/requirements') {
      return ok(route, { total: 0, page: 1, page_size: 20, items: [] })
    }
    if (apiPath === '/test-cases/domains') {
      return ok(route, [
        {
          domain: 'Web 平台',
          count: TEST_CASES.length,
          modules: [
            { module: '账号与权限', count: 12 },
            { module: '报告与追溯', count: 12 },
          ],
        },
      ])
    }
    if (apiPath === '/test-cases') {
      const pageNumber = Number(url.searchParams.get('page') || 1)
      const pageSize = Number(url.searchParams.get('page_size') || 20)
      const keyword = url.searchParams.get('keyword')?.trim() || ''
      if (options.slowTestcaseKeyword && keyword === options.slowTestcaseKeyword) {
        await new Promise((resolve) => setTimeout(resolve, 400))
      }
      const filtered = keyword
        ? TEST_CASES.filter((item) => item.title.includes(keyword))
        : TEST_CASES
      const start = (pageNumber - 1) * pageSize
      return ok(route, {
        total: filtered.length,
        page: pageNumber,
        page_size: pageSize,
        items: filtered.slice(start, start + pageSize),
      })
    }
    return route.abort('blockedbyclient')
  })
}

async function openPage(page: Page, path: string, heading: string) {
  await page.goto(path)
  await expect(page.getByRole('heading', { level: 1, name: heading, exact: true })).toBeVisible()
  await page.waitForLoadState('networkidle')
}

async function expectNoGlobalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)
}

test.describe('Batch 53 populated Obsidian production contract', () => {
  test.use({ hasTouch: true })

  test('populated testcase is accessible and locally scrollable on mobile', async ({ page }) => {
    await installFixtures(page)
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/testcase', '用例服务')
    await expectNoGlobalOverflow(page)

    const tableRegion = page.getByRole('region', { name: '测试用例数据表' })
    await expect(tableRegion).toBeVisible()
    await expect(tableRegion).toHaveAttribute('tabindex', '0')
    const firstRowDelete = page.getByRole('button', {
      name: `删除用例：${TEST_CASES[0].title}`,
    })
    await expect(firstRowDelete).toBeVisible()
    const actionBox = await firstRowDelete.boundingBox()
    expect(actionBox?.x ?? VIEWPORTS[0].width).toBeLessThan(VIEWPORTS[0].width)

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    expect(
      results.violations.map(({ id, impact, nodes }) => ({
        id,
        impact,
        nodes: nodes.length,
        targets: nodes.slice(0, 8).map((node) => node.target),
      })),
    ).toEqual([])
  })

  test('mobile testcase controls meet the 44px production touch contract', async ({ page }) => {
    await installFixtures(page)
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/testcase', '用例服务')

    const controls = page.locator(
      'main button:visible, main input:visible, main [role="checkbox"]:visible, main [role="combobox"]:visible',
    )
    const undersized = await controls.evaluateAll((nodes) =>
      nodes.flatMap((node) => {
        const rect = node.getBoundingClientRect()
        if (rect.width >= 44 && rect.height >= 44) return []
        return [
          {
            tag: node.tagName,
            name:
              node.getAttribute('aria-label') ||
              node.getAttribute('placeholder') ||
              node.textContent?.trim().slice(0, 30) ||
              '(unnamed)',
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
        ]
      }),
    )
    expect(undersized).toEqual([])
  })

  test('workbench charts expose summaries and structured data without duplicate KPI cards', async ({
    page,
  }) => {
    await installFixtures(page)
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/workbench', '工作台')
    await expectNoGlobalOverflow(page)

    await expect(page.getByRole('figure', { name: '项目概览' })).toBeVisible()
    await expect(page.getByRole('table', { name: '项目概览数据' })).toBeAttached()
    await expect(page.getByRole('figure', { name: '用例优先级分布' })).toBeVisible()
    await expect(page.getByRole('table', { name: '用例优先级分布数据' })).toBeAttached()
    await expect(page.getByTestId('workbench-summary-cards')).toHaveCount(0)

    await page.getByRole('tab', { name: '多项目概览' }).click()
    await expect(page.getByRole('figure', { name: '整体通过率趋势（近 7 天）' })).toBeVisible()
    await expect(page.getByRole('table', { name: '整体通过率趋势数据' })).toBeAttached()
    await expect(page.getByRole('figure', { name: '缺陷趋势（近 7 天）' })).toBeVisible()
    await expect(page.getByRole('table', { name: '缺陷趋势数据' })).toBeAttached()
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    expect(results.violations).toEqual([])
  })

  test('workbench preserves loading space and recovers inline from one failed request', async ({ page }) => {
    await installFixtures(page, { dashboardFailureOnce: true })
    const dashboardRequests: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/dashboard/stats')) {
        dashboardRequests.push(request.url())
      }
    })

    await page.goto('/workbench')
    await expect(page.getByRole('heading', { level: 1, name: '工作台' })).toBeVisible()
    await expect(page.locator('[aria-busy="true"][aria-label="加载中"]').first()).toBeVisible()
    const error = page.getByRole('alert')
    await expect(error).toContainText('统计服务暂时不可用')
    await error.getByRole('button', { name: '重新加载' }).click()
    await expect(page.getByRole('figure', { name: /项目概览/ })).toBeVisible()
    expect(dashboardRequests).toHaveLength(2)
  })

  test('testcase search sends one request per submit and ignores a superseded slow result', async ({ page }) => {
    await installFixtures(page, { slowTestcaseKeyword: '超长标题' })
    await openPage(page, '/testcase', '用例服务')

    const testcaseRequests: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/test-cases?')) {
        testcaseRequests.push(request.url())
      }
    })

    const search = page.getByPlaceholder('搜索标题/关键字')
    await search.fill('超长标题')
    await page.waitForTimeout(120)
    expect(testcaseRequests).toHaveLength(0)

    const slowRequest = page.waitForRequest((request) =>
      request.url().includes('keyword=%E8%B6%85%E9%95%BF%E6%A0%87%E9%A2%98'),
    )
    await page.getByRole('button', { name: '搜索', exact: true }).click()
    await slowRequest

    await search.fill('生产级测试用例 02')
    const fastResponse = page.waitForResponse((response) =>
      response.url().includes('keyword=%E7%94%9F%E4%BA%A7%E7%BA%A7%E6%B5%8B%E8%AF%95%E7%94%A8%E4%BE%8B+02'),
    )
    await page.getByRole('button', { name: '搜索', exact: true }).click()
    await fastResponse

    await expect(page.getByText('生产级测试用例 02', { exact: true })).toBeVisible()
    await page.waitForTimeout(450)
    await expect(page.getByText(TEST_CASES[0].title, { exact: true })).toHaveCount(0)
    expect(testcaseRequests).toHaveLength(2)
  })

  test('mobile navigation exposes current page and closes after route change', async ({ page }) => {
    await installFixtures(page)
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/workbench', '工作台')

    await page.getByRole('button', { name: 'Toggle Sidebar' }).click()
    const current = page.getByRole('button', { name: '工作台', exact: true })
    await expect(current).toHaveAttribute('aria-current', 'page')

    const target = page.getByRole('button', { name: '用例服务', exact: true })
    await target.click()
    await expect(page).toHaveURL(/\/testcase$/)
    await expect(page.getByRole('heading', { level: 1, name: '用例服务' })).toBeVisible()
    await expect(target).not.toBeVisible()

    await page.getByRole('button', { name: 'Toggle Sidebar' }).click()
    await expect(page.getByRole('button', { name: '用例服务', exact: true })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  test('navigation load failure stays in context and can be retried', async ({ page }) => {
    await installFixtures(page, { menuFailureOnce: true })
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/workbench', '工作台')
    await page.getByRole('button', { name: 'Toggle Sidebar' }).click()

    const error = page.getByRole('alert')
    await expect(error).toContainText('导航菜单加载失败')
    await error.getByRole('button', { name: '重新加载导航菜单' }).click()
    await expect(page.getByRole('button', { name: '工作台', exact: true })).toBeVisible()
    await expect(error).toHaveCount(0)
  })

  test('integration form exposes inline errors and focuses the first invalid field', async ({
    page,
  }) => {
    await installFixtures(page)
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/integration', '集成配置')
    await page.getByRole('button', { name: '新建集成' }).click()
    await page.getByRole('button', { name: '创建', exact: true }).click()

    const name = page.getByLabel('名称 *')
    const baseUrl = page.getByLabel('Base URL *')
    await expect(name).toHaveAttribute('aria-invalid', 'true')
    await expect(baseUrl).toHaveAttribute('aria-invalid', 'true')
    await expect(page.getByText('名称不能为空', { exact: true })).toBeVisible()
    await expect(page.getByText('Base URL 不能为空', { exact: true })).toBeVisible()
    await expect(name).toBeFocused()
  })

  test('valid integration submit is single-shot, disabled while saving and refreshes the card', async ({ page }) => {
    await installFixtures(page, { integrationCreate: true })
    const createRequests: string[] = []
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().endsWith('/api/v1/integrations')) {
        createRequests.push(request.url())
      }
    })

    await openPage(page, '/integration', '集成配置')
    await page.getByRole('button', { name: '新建集成' }).click()
    await page.getByLabel('名称 *').fill('Batch 53 新建集成')
    await page.getByLabel('Base URL *').fill('https://jira.example.invalid')

    const submit = page.getByRole('button', { name: '创建', exact: true })
    await submit.click()
    await expect(submit).toBeDisabled()
    await expect(page.getByText('Batch 53 新建集成', { exact: true })).toBeVisible()
    expect(createRequests).toHaveLength(1)
  })

  test('destructive integration action requires an accessible in-product confirmation', async ({ page }) => {
    await installFixtures(page, { integrationItem: true })
    await openPage(page, '/integration', '集成配置')

    const deleteButton = page.getByRole('button', { name: '删除集成配置 Batch 53 Jira' })
    await deleteButton.click()
    const dialog = page.getByRole('alertdialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('删除集成配置')
    await expect(dialog).toContainText('Batch 53 Jira')

    await dialog.getByRole('button', { name: '取消' }).click()
    await expect(page.getByText('Batch 53 Jira')).toBeVisible()
    await expect(deleteButton).toBeFocused()

    await deleteButton.click()
    await page.getByRole('alertdialog').getByRole('button', { name: '确认删除' }).click()
    await expect(page.getByText('暂无集成配置')).toBeVisible()
  })

  test('professional graph workspaces adapt without clipping and expose text alternatives', async ({ page }) => {
    await installFixtures(page)
    await page.setViewportSize(VIEWPORTS[0])

    await openPage(page, '/knowledge?tab=graph', '知识中心')
    await expect(page.getByRole('img', { name: '知识图谱，共 2 个节点、1 条关系' })).toBeVisible()
    await expect(page.getByRole('button', { name: '放大知识图谱' })).toBeVisible()
    await expectNoGlobalOverflow(page)

    await openPage(page, '/knowledge?tab=sphere', '知识中心')
    await expect(page.getByRole('img', { name: '项目球知识图谱，共 2 个节点、1 条关系' })).toBeVisible()
    await expectNoGlobalOverflow(page)

    await page.getByRole('radio', { name: '列表视图' }).click()
    await expect(page.getByRole('region', { name: '知识球关系列表' })).toBeVisible()

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    expect(results.violations).toEqual([])
  })

  test('version panorama and page interaction panel adapt to a narrow viewport', async ({ page }) => {
    await installFixtures(page)
    const failedRequests: string[] = []
    page.on('requestfailed', (request) => failedRequests.push(request.url()))
    await page.setViewportSize(VIEWPORTS[0])
    await page.goto('/release-bundles/53/panorama')
    await expect(page.getByRole('heading', { level: 1, name: 'Batch 53' })).toBeVisible()
    await expect(page.getByText('用户端 53.0.0 / 运营后台 53.0.0')).toBeVisible()
    await expectNoGlobalOverflow(page)

    await page.getByRole('button', { name: /登录页/ }).click()
    const panel = page.getByRole('dialog', { name: '登录页' })
    await expect(panel).toBeVisible()
    await expect(panel).toContainText('提交登录表单')
    await expect(panel).toContainText('工作台')
    await expectNoGlobalOverflow(page)
    expect(failedRequests).toEqual([])

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    expect(results.violations).toEqual([])
  })

  test('core tasks remain reachable at 200 percent text size and mobile landscape', async ({ page }) => {
    await installFixtures(page)
    await page.addInitScript(() => {
      document.documentElement.style.fontSize = '200%'
    })
    await page.setViewportSize(VIEWPORTS[0])
    await openPage(page, '/testcase', '用例服务')
    await expectNoGlobalOverflow(page)
    await expect(page.getByRole('button', { name: `删除用例：${TEST_CASES[0].title}` })).toBeVisible()

    await page.setViewportSize({ width: 844, height: 390 })
    await openPage(page, '/workbench', '工作台')
    await expectNoGlobalOverflow(page)
    await expect(page.getByRole('figure', { name: /项目概览/ })).toBeVisible()
  })

  for (const viewport of VIEWPORTS) {
    test(`populated core pages remain stable at ${viewport.id}`, async ({ page }) => {
      await installFixtures(page)
      await page.setViewportSize(viewport)
      for (const [path, heading] of [
        ['/workbench', '工作台'],
        ['/testcase', '用例服务'],
      ] as const) {
        await openPage(page, path, heading)
        await expectNoGlobalOverflow(page)
      }
    })
  }
})
