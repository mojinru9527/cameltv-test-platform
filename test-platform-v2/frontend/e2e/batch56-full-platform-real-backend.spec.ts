import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type Request, type TestInfo } from '@playwright/test'

const credentials = {
  username: process.env.E2E_USERNAME?.trim() ?? '',
  password: process.env.E2E_PASSWORD?.trim() ?? '',
}

const configuredFixtureIds = {
  requirementReviewId: Number(process.env.E2E_REQUIREMENT_REVIEW_ID || 0),
  testPlanId: Number(process.env.E2E_TEST_PLAN_ID || 0),
  releaseBundleId: Number(process.env.E2E_RELEASE_BUNDLE_ID || 0),
}

type RouteExpectation = {
  path: string
  expectedPath?: string
  heading?: string
  fallbackText?: string
  navLabel?: string
  controlledUnavailable?: {
    method: string
    pathname: string
    status: number
    uiHeading: string
    uiDescription: string
    blocker: string
  }
}

type DynamicFixtures = {
  requirementReviewId: number
  requirementTitle: string
  testPlanId: number
  testPlanName: string
  releaseBundleId: number
  releaseBundleName: string
  createdTestPlanId: number
  createdReleaseBundleId: number
}

type RuntimeSnapshot = {
  consoleErrors: ConsoleError[]
  pageErrors: string[]
  failedRequests: string[]
  failedResponses: FailedResponse[]
  duplicateGets: string[]
}

type ConsoleError = {
  text: string
  url: string
}

type FailedResponse = {
  status: number
  method: string
  url: string
}

type RouteResult = {
  path: string
  actualPath: string
  viewport: AcceptanceViewport
  theme?: string
  mode?: 'light' | 'dark'
  issues: string[]
  controlledBlockers: string[]
  runtime: RuntimeSnapshot
}

type ThemeContext = {
  theme: 'cyberpunk' | 'apple' | 'clay' | 'xlab' | 'liquid-glass' | 'obsidian-flow'
  mode: 'light' | 'dark'
}

type AcceptanceViewport = 'desktop' | 'tablet' | 'mobile'

const viewportSizes: Record<AcceptanceViewport, { width: number; height: number }> = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
}

const pcThemeModes: readonly ThemeContext[] = [
  { theme: 'cyberpunk', mode: 'light' },
  { theme: 'cyberpunk', mode: 'dark' },
  { theme: 'apple', mode: 'light' },
  { theme: 'apple', mode: 'dark' },
  { theme: 'clay', mode: 'light' },
  { theme: 'clay', mode: 'dark' },
  { theme: 'xlab', mode: 'light' },
  { theme: 'xlab', mode: 'dark' },
  { theme: 'liquid-glass', mode: 'light' },
  { theme: 'liquid-glass', mode: 'dark' },
  { theme: 'obsidian-flow', mode: 'dark' },
]

const desktopRoutes: RouteExpectation[] = [
  { path: '/', expectedPath: '/workbench', heading: '工作台', navLabel: '工作台' },
  { path: '/workbench', heading: '工作台', navLabel: '工作台' },
  { path: '/trace', heading: '质量追溯', navLabel: '质量追溯' },
  { path: '/requirement', heading: '需求文档', navLabel: '需求文档' },
  { path: '/testcase', heading: '用例服务', navLabel: '用例服务' },
  { path: '/testplan', heading: '测试计划', navLabel: '测试计划' },
  { path: '/mindmap', heading: '脑图视图', navLabel: '用例脑图' },
  { path: '/apitest', heading: '接口测试', navLabel: '接口测试' },
  { path: '/uitest', heading: 'UI 测试', navLabel: 'UI 自动化' },
  { path: '/special', heading: '音视频检测', navLabel: '专项测试' },
  { path: '/schedule', heading: '定时任务', navLabel: '定时任务' },
  { path: '/defect', heading: '缺陷管理' },
  { path: '/report', heading: '报告中心', navLabel: '报告中心' },
  { path: '/system', heading: '系统管理', navLabel: '系统管理' },
  { path: '/project', heading: '项目管理', navLabel: '项目管理' },
  { path: '/notify', heading: '通知配置' },
  { path: '/environment', heading: '环境与变量管理' },
  { path: '/dataset', heading: '测试数据集' },
  { path: '/integration', heading: '集成配置' },
  { path: '/knowledge', heading: '知识中心', navLabel: '知识中心' },
  {
    path: '/version-mission',
    expectedPath: '/release-bundles',
    heading: '版本发布包',
  },
  { path: '/release-bundles', heading: '版本发布包' },
  { path: '/agent-workbench', heading: 'Agent 工作台', navLabel: 'Agent 工作台' },
  {
    path: '/perftest',
    heading: '性能测试',
    navLabel: '性能监控',
    controlledUnavailable: {
      method: 'GET',
      pathname: '/api/v1/perf-sessions/devices',
      status: 503,
      uiHeading: '真实性能采集不可用',
      uiDescription: '不会生成模拟数据',
      blocker: 'J18 BLOCKED：SoloX 未部署，无法执行真实 Android/iOS 性能采集',
    },
  },
  {
    path: '/theme-lab',
    fallbackText: '测试平台 · 主题实验室',
  },
  { path: '/batch56-route-not-found', heading: '页面建设中' },
]

const mobileRoutePaths = new Set([
  '/workbench',
  '/requirement',
  '/testcase',
  '/testplan',
  '/apitest',
  '/uitest',
  '/defect',
  '/report',
  '/system',
  '/environment',
  '/knowledge',
  '/release-bundles',
])

function attachRuntimeProbe(page: Page) {
  let consoleErrors: ConsoleError[] = []
  let pageErrors: string[] = []
  let failedRequests: string[] = []
  let failedResponses: FailedResponse[] = []
  let successfulGetCounts = new Map<string, number>()
  const pendingBusinessRequests = new Set<Request>()

  const isBusinessRequest = (request: Request) =>
    request.url().includes('/api/v1/')
    && ['fetch', 'xhr'].includes(request.resourceType())

  const normalizeUrl = (rawUrl: string) => {
    const url = new URL(rawUrl)
    const sortedParams = [...url.searchParams.entries()]
      .filter(([key]) => !['_', 'cacheBust', 'timestamp'].includes(key))
      .sort(([leftKey, leftValue], [rightKey, rightValue]) =>
        leftKey.localeCompare(rightKey) || leftValue.localeCompare(rightValue),
      )
    url.search = ''
    for (const [key, value] of sortedParams) url.searchParams.append(key, value)
    return `${url.origin}${url.pathname}${url.search}`
  }

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push({
        text: message.text(),
        url: message.location().url,
      })
    }
  })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('request', (request) => {
    if (isBusinessRequest(request)) pendingBusinessRequests.add(request)
  })
  page.on('requestfinished', (request) => pendingBusinessRequests.delete(request))
  page.on('requestfailed', (request) => {
    pendingBusinessRequests.delete(request)
    const failure = request.failure()?.errorText || 'unknown error'
    if (!failure.includes('ERR_ABORTED')) {
      failedRequests.push(`${request.method()} ${request.url()} — ${failure}`)
    }
  })
  page.on('response', (response) => {
    const request = response.request()
    // A streaming/long-lived response may never emit requestfinished. Once
    // headers arrive, its HTTP status is observable and it must not keep every
    // subsequent route in a permanent "busy" state.
    pendingBusinessRequests.delete(request)
    const isBusinessApi = response.url().includes('/api/v1/')
    if (isBusinessApi && response.status() >= 400) {
      failedResponses.push({
        status: response.status(),
        method: request.method(),
        url: response.url(),
      })
    }
    if (isBusinessApi && request.method() === 'GET' && response.status() < 400) {
      const key = normalizeUrl(response.url())
      successfulGetCounts.set(key, (successfulGetCounts.get(key) || 0) + 1)
    }
  })

  return {
    reset() {
      consoleErrors = []
      pageErrors = []
      failedRequests = []
      failedResponses = []
      successfulGetCounts = new Map<string, number>()
    },
    snapshot(): RuntimeSnapshot {
      const duplicateGets = [...successfulGetCounts.entries()]
        .filter(([, count]) => count > 1)
        .map(([url, count]) => `${count} × GET ${url}`)
      return {
        consoleErrors: [...consoleErrors],
        pageErrors: [...pageErrors],
        failedRequests: [...failedRequests],
        failedResponses: [...failedResponses],
        duplicateGets,
      }
    },
    async waitForBusinessIdle(timeout = 5_000, quietPeriod = 250) {
      const deadline = Date.now() + timeout
      let quietSince = 0
      while (Date.now() < deadline) {
        if (pendingBusinessRequests.size === 0) {
          if (quietSince === 0) quietSince = Date.now()
          if (Date.now() - quietSince >= quietPeriod) return true
        } else {
          quietSince = 0
        }
        await new Promise((resolve) => setTimeout(resolve, 50))
      }
      return false
    },
  }
}

function formatFailedResponse(response: FailedResponse) {
  return `${response.status} ${response.method} ${response.url}`
}

function formatConsoleError(error: ConsoleError) {
  return error.url ? `${error.text} (${error.url})` : error.text
}

async function waitForUiToSettle(
  page: Page,
  probe: ReturnType<typeof attachRuntimeProbe>,
) {
  await page.waitForLoadState('domcontentloaded')
  return probe.waitForBusinessIdle()
}

async function login(page: Page, probe: ReturnType<typeof attachRuntimeProbe>) {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'CamelTv 测试平台' })).toBeVisible()
  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/auth/login')
      && response.request().method() === 'POST',
  )
  await page.locator('input[name="username"]').fill(credentials.username)
  await page.locator('input[type="password"]').fill(credentials.password)
  await page.locator('button[type="submit"]').click()

  const response = await loginResponsePromise
  expect(response.ok(), `登录接口返回 HTTP ${response.status()}`).toBe(true)
  const body = await response.json()
  expect(body?.code, body?.msg || '登录接口未返回成功业务码').toBe(0)
  const projectId = Number(body?.data?.projects?.[0]?.id)
  expect(projectId, '登录账号必须至少关联一个项目').toBeGreaterThan(0)
  await expect(page).toHaveURL(/\/workbench$/, { timeout: 15_000 })
  await expect(page.getByRole('heading', { name: '工作台', exact: true })).toBeVisible()
  expect(
    await waitForUiToSettle(page, probe),
    '登录后业务 API 未在 5 秒内稳定',
  ).toBe(true)
  return projectId
}

async function createDynamicFixtures(page: Page, projectId: number): Promise<DynamicFixtures> {
  return page.evaluate(
    async ({ projectId: activeProjectId, configuredIds }) => {
      const headers = {
        'Content-Type': 'application/json',
        'X-Project-Id': String(activeProjectId),
      }

      const request = async (
        path: string,
        options: { method?: string; body?: Record<string, unknown> } = {},
      ) => {
        const response = await fetch(`/api/v1${path}`, {
          method: options.method || 'GET',
          credentials: 'include',
          headers,
          body: options.body ? JSON.stringify(options.body) : undefined,
        })
        const envelope = await response.json().catch(() => null)
        return { response, envelope }
      }

      const requireSuccess = (
        result: { response: Response; envelope: any },
        description: string,
      ) => {
        if (!result.response.ok || result.envelope?.code !== 0) {
          throw new Error(
            `${description}失败：HTTP ${result.response.status}，${result.envelope?.msg || '无业务错误信息'}`,
          )
        }
        return result.envelope.data
      }

      let createdTestPlanId = 0
      let createdReleaseBundleId = 0
      try {
        const stamp = Date.now()

        let testPlanId = Number.isInteger(configuredIds.testPlanId) && configuredIds.testPlanId > 0
          ? configuredIds.testPlanId
          : 0
        let testPlanName = ''
        if (testPlanId) {
          const data = requireSuccess(
            await request(`/test-plans/${testPlanId}`),
            `读取指定测试计划 #${testPlanId}`,
          )
          testPlanName = data.name
        } else {
          const list = requireSuccess(
            await request('/test-plans?page=1&page_size=1'),
            '读取测试计划列表',
          )
          const existing = list.items?.[0]
          if (existing) {
            testPlanId = Number(existing.id)
            testPlanName = existing.name
          } else {
            const created = requireSuccess(
              await request('/test-plans', {
                method: 'POST',
                body: {
                  plan_id: `B56-ROUTE-${stamp}`,
                  name: `Batch56 动态路由验收 ${stamp}`,
                  description: 'Batch56 真实后端动态路由验收临时数据',
                },
              }),
              '创建临时测试计划',
            )
            testPlanId = Number(created.id)
            testPlanName = created.name
            createdTestPlanId = testPlanId
          }
        }

        let releaseBundleId =
          Number.isInteger(configuredIds.releaseBundleId) && configuredIds.releaseBundleId > 0
            ? configuredIds.releaseBundleId
            : 0
        let releaseBundleName = ''
        if (releaseBundleId) {
          const data = requireSuccess(
            await request(`/release-bundles/${releaseBundleId}`),
            `读取指定发布包 #${releaseBundleId}`,
          )
          releaseBundleName = data.name
        } else {
          const list = requireSuccess(
            await request('/release-bundles?page=1&page_size=1'),
            '读取发布包列表',
          )
          const existing = list.items?.[0]
          if (existing) {
            releaseBundleId = Number(existing.id)
            releaseBundleName = existing.name
          } else {
            const created = requireSuccess(
              await request('/release-bundles', {
                method: 'POST',
                body: {
                  name: `Batch56 动态路由验收 ${stamp}`,
                  description: 'Batch56 真实后端动态路由验收临时数据',
                  client_version: 'batch56-e2e',
                  admin_version: 'batch56-e2e',
                },
              }),
              '创建临时发布包',
            )
            releaseBundleId = Number(created.id)
            releaseBundleName = created.name
            createdReleaseBundleId = releaseBundleId
          }
        }

        let requirementReviewId =
          Number.isInteger(configuredIds.requirementReviewId) && configuredIds.requirementReviewId > 0
            ? configuredIds.requirementReviewId
            : 0
        let requirementTitle = ''

        if (requirementReviewId) {
          const review = requireSuccess(
            await request(`/requirements/${requirementReviewId}/review-state`),
            `读取指定需求审查队列 #${requirementReviewId}`,
          )
          requirementTitle = review.document_title
        } else {
          const requirements = requireSuccess(
            await request('/requirements?page=1&page_size=20'),
            '读取需求文档列表',
          )
          for (const item of requirements.items || []) {
            const candidate = await request(`/requirements/${item.id}/review-state`)
            if (candidate.response.ok && candidate.envelope?.code === 0) {
              requirementReviewId = Number(item.id)
              requirementTitle = candidate.envelope.data.document_title
              break
            }
          }
        }

        return {
          requirementReviewId,
          requirementTitle,
          testPlanId,
          testPlanName,
          releaseBundleId,
          releaseBundleName,
          createdTestPlanId,
          createdReleaseBundleId,
        }
      } catch (error) {
        for (const [path, id] of [
          ['/test-plans', createdTestPlanId],
          ['/release-bundles', createdReleaseBundleId],
        ] as const) {
          if (id) {
            await fetch(`/api/v1${path}/${id}`, {
              method: 'DELETE',
              credentials: 'include',
              headers,
            }).catch(() => undefined)
          }
        }
        throw error
      }
    },
    { projectId, configuredIds: configuredFixtureIds },
  )
}

async function cleanupDynamicFixtures(page: Page, projectId: number, fixtures: DynamicFixtures) {
  await page.evaluate(
    async ({ activeProjectId, planId, bundleId }) => {
      const headers = { 'X-Project-Id': String(activeProjectId) }
      const failures: string[] = []
      for (const [path, id] of [
        ['/test-plans', planId],
        ['/release-bundles', bundleId],
      ] as const) {
        if (!id) continue
        const response = await fetch(`/api/v1${path}/${id}`, {
          method: 'DELETE',
          credentials: 'include',
          headers,
        })
        const body = await response.json().catch(() => null)
        if (!response.ok || body?.code !== 0) {
          failures.push(`${path}/${id}: HTTP ${response.status} ${body?.msg || ''}`)
        }
      }
      if (failures.length > 0) {
        throw new Error(`Batch56 临时动态路由数据清理失败：${failures.join('；')}`)
      }
    },
    {
      activeProjectId: projectId,
      planId: fixtures.createdTestPlanId,
      bundleId: fixtures.createdReleaseBundleId,
    },
  )
}

function dynamicRoutes(fixtures: DynamicFixtures): RouteExpectation[] {
  const requirementRoute = fixtures.requirementReviewId
    ? {
        path: `/requirement/${fixtures.requirementReviewId}/review`,
        heading: fixtures.requirementTitle,
        navLabel: '需求文档',
      }
    : {
        path: '/requirement/0/review',
        fallbackText: '无效的需求文档 ID',
        navLabel: '需求文档',
      }

  return [
    requirementRoute,
    {
      path: `/testplan/${fixtures.testPlanId}`,
      heading: fixtures.testPlanName,
      navLabel: '测试计划',
    },
    {
      path: `/release-bundles/${fixtures.releaseBundleId}`,
      heading: fixtures.releaseBundleName,
    },
    {
      path: `/release-bundles/${fixtures.releaseBundleId}/panorama`,
      heading: fixtures.releaseBundleName,
    },
  ]
}

async function navigateInApp(page: Page, path: string) {
  await page.evaluate((nextPath) => {
    window.history.pushState({}, '', nextPath)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, path)
}

async function inspectRoute(
  page: Page,
  route: RouteExpectation,
  viewport: AcceptanceViewport,
  probe: ReturnType<typeof attachRuntimeProbe>,
  themeContext?: ThemeContext,
): Promise<RouteResult> {
  const issues: string[] = []
  const controlledBlockers: string[] = []
  probe.reset()

  try {
    await navigateInApp(page, route.path)
    const expectedPath = route.expectedPath || route.path
    await page.waitForFunction(
      (pathname) => window.location.pathname === pathname,
      expectedPath,
      { timeout: 12_000 },
    )

    const expectedContent = route.heading || route.fallbackText
    if (expectedContent) {
      const locator = route.heading
        ? page.getByRole('heading', { name: expectedContent, exact: true }).first()
        : page.getByText(expectedContent, { exact: false }).first()
      await locator.waitFor({ state: 'visible', timeout: 12_000 })
    }
    if (!(await waitForUiToSettle(page, probe))) {
      issues.push('业务 API 未在 5 秒内稳定')
    }
  } catch (error) {
    issues.push(error instanceof Error ? error.message : String(error))
  }

  const actualPath = new URL(page.url()).pathname
  const expectedPath = route.expectedPath || route.path
  if (actualPath !== expectedPath) {
    issues.push(`路由未落在预期地址：期望 ${expectedPath}，实际 ${actualPath}`)
  }

  const main = page.locator('#main-content')
  if (!(await main.isVisible().catch(() => false))) {
    issues.push('主内容区域不可见')
  }
  const mainText = await main.innerText().catch(() => '')
  if (mainText.trim().length < 20) {
    issues.push(`主内容文本过少，疑似白屏（${mainText.trim().length} 字符）`)
  }
  if (await page.getByText('页面出现异常', { exact: true }).isVisible().catch(() => false)) {
    issues.push('触发全局 ErrorBoundary：页面出现异常')
  }

  if (route.navLabel) {
    if (viewport === 'mobile') {
      const trigger = page.getByRole('button', { name: 'Toggle Sidebar', exact: true })
      const drawer = page.locator('[data-mobile="true"][data-sidebar="sidebar"]')
      try {
        await trigger.click({ timeout: 5_000 })
        await drawer.waitFor({ state: 'visible', timeout: 5_000 })
        const activeNav = drawer
          .locator('[aria-current="page"]')
          .filter({ hasText: route.navLabel })
        if ((await activeNav.count()) === 0) {
          issues.push(`主导航未高亮：${route.navLabel}`)
        }
      } catch (error) {
        issues.push(
          `移动端主导航抽屉无法打开：${error instanceof Error ? error.message : String(error)}`,
        )
      } finally {
        if (await drawer.isVisible().catch(() => false)) {
          const overlay = page.locator('[data-slot="sheet-overlay"]')
          const overlayBox = await overlay.boundingBox().catch(() => null)
          if (overlayBox) {
            await page.mouse.click(
              overlayBox.x + overlayBox.width - 10,
              overlayBox.y + overlayBox.height / 2,
            )
          } else {
            // A tooltip can consume the first Escape; the second one closes
            // the underlying Radix sheet.
            await page.keyboard.press('Escape')
            await page.keyboard.press('Escape')
          }
          await drawer.waitFor({ state: 'hidden', timeout: 2_000 }).catch(() => {
            issues.push('移动端主导航抽屉无法关闭')
          })
        }
      }
    } else {
      const activeNav = page
        .locator('[aria-label="主导航"] [aria-current="page"]')
        .filter({ hasText: route.navLabel })
      if ((await activeNav.count()) === 0) {
        issues.push(`主导航未高亮：${route.navLabel}`)
      }
    }
  }

  const hasDocumentOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  )
  if (hasDocumentOverflow) {
    const viewportLabel = viewport === 'desktop' ? 'PC' : viewport === 'tablet' ? '平板' : '移动端'
    issues.push(`${viewportLabel}出现页面级横向溢出`)
  }

  if (themeContext) {
    const renderedTheme = await page.locator('html').getAttribute('data-theme')
    const renderedClasses = (await page.locator('html').getAttribute('class')) || ''
    if (renderedTheme !== themeContext.theme) {
      issues.push(`主题未生效：期望 ${themeContext.theme}，实际 ${renderedTheme || '空'}`)
    }
    if (!renderedClasses.split(/\s+/).includes(themeContext.mode)) {
      issues.push(`明暗模式未生效：期望 ${themeContext.mode}，实际 class="${renderedClasses}"`)
    }

    await page.keyboard.press('Tab')
    const focusState = await page.evaluate(() => {
      const active = document.activeElement
      return {
        tag: active?.tagName || '',
        hidden: active instanceof HTMLElement
          ? active.getClientRects().length === 0
          : true,
      }
    })
    if (!focusState.tag || ['BODY', 'HTML'].includes(focusState.tag) || focusState.hidden) {
      issues.push('键盘 Tab 未落在可见的可聚焦元素')
    }

    const axe = await new AxeBuilder({ page })
      .include('#main-content')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    const blockingViolations = axe.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    )
    if (blockingViolations.length > 0) {
      issues.push(
        `Axe serious/critical：${blockingViolations
          .map((violation) => {
            const firstTarget = violation.nodes[0]?.target.join(' ') || 'unknown'
            return `${violation.id}(${violation.nodes.length})[${firstTarget}]`
          })
          .join(' | ')}`,
      )
    }
  }

  const runtime = probe.snapshot()
  let unexpectedConsoleErrors = runtime.consoleErrors
  let unexpectedFailedResponses = runtime.failedResponses
  if (route.controlledUnavailable) {
    const expected = route.controlledUnavailable
    const controlledResponses = runtime.failedResponses.filter((response) => {
      const pathname = new URL(response.url).pathname
      return response.status === expected.status
        && response.method === expected.method
        && pathname === expected.pathname
    })
    unexpectedFailedResponses = runtime.failedResponses.filter(
      (response) => !controlledResponses.includes(response),
    )

    if (controlledResponses.length > 0) {
      controlledBlockers.push(expected.blocker)
      unexpectedConsoleErrors = runtime.consoleErrors.filter((error) => {
        const errorPathname = error.url ? new URL(error.url).pathname : ''
        const isExpectedResourceError =
          error.text.includes(`status of ${expected.status}`)
          || error.text.includes(`status code ${expected.status}`)
        return errorPathname !== expected.pathname
          && !(errorPathname === '' && isExpectedResourceError)
      })
      const unavailableAlert = page.getByRole('alert').filter({ hasText: expected.uiHeading })
      if (!(await unavailableAlert.isVisible().catch(() => false))) {
        issues.push(`受控 ${expected.status} 未呈现不可用态：${expected.uiHeading}`)
      } else if (
        !(await unavailableAlert.getByText(expected.uiDescription, { exact: false })
          .isVisible()
          .catch(() => false))
      ) {
        issues.push(`不可用态未说明真实数据策略：${expected.uiDescription}`)
      }
      if (controlledResponses.length > 1) {
        issues.push(
          `受控不可用接口重复请求：${controlledResponses.length} × ${expected.method} ${expected.pathname}`,
        )
      }
    } else if (
      await page.getByRole('alert').filter({ hasText: expected.uiHeading })
        .isVisible()
        .catch(() => false)
    ) {
      issues.push(`未观察到 ${expected.status} 却呈现不可用态：${expected.uiHeading}`)
    }
  }
  if (unexpectedConsoleErrors.length > 0) {
    issues.push(
      `console.error：${unexpectedConsoleErrors.map(formatConsoleError).join(' | ')}`,
    )
  }
  if (runtime.pageErrors.length > 0) {
    issues.push(`pageerror：${runtime.pageErrors.join(' | ')}`)
  }
  if (runtime.failedRequests.length > 0) {
    issues.push(`请求传输失败：${runtime.failedRequests.join(' | ')}`)
  }
  if (unexpectedFailedResponses.length > 0) {
    issues.push(
      `API 错误响应：${unexpectedFailedResponses.map(formatFailedResponse).join(' | ')}`,
    )
  }
  if (runtime.duplicateGets.length > 0) {
    issues.push(`重复有效 GET：${runtime.duplicateGets.join(' | ')}`)
  }

  return {
    path: route.path,
    actualPath,
    viewport,
    theme: themeContext?.theme,
    mode: themeContext?.mode,
    issues,
    controlledBlockers,
    runtime,
  }
}

async function runRouteMatrix(
  page: Page,
  testInfo: TestInfo,
  viewport: AcceptanceViewport,
  fixtures: DynamicFixtures,
  probe: ReturnType<typeof attachRuntimeProbe>,
  themeContext?: ThemeContext,
) {
  await page.setViewportSize(viewportSizes[viewport])
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const routes = [
    ...(viewport !== 'mobile'
      ? desktopRoutes
      : desktopRoutes.filter((route) => mobileRoutePaths.has(route.path))),
    ...dynamicRoutes(fixtures),
  ]
  const results: RouteResult[] = []

  for (const route of routes) {
    results.push(await inspectRoute(page, route, viewport, probe, themeContext))
  }

  const evidenceSuffix = themeContext
    ? `${viewport}-${themeContext.theme}-${themeContext.mode}`
    : viewport
  await testInfo.attach(`batch57-${evidenceSuffix}-route-matrix.json`, {
    body: Buffer.from(JSON.stringify(results, null, 2)),
    contentType: 'application/json',
  })

  return results
}

async function runAcceptanceViewport(
  page: Page,
  testInfo: TestInfo,
  viewport: AcceptanceViewport,
  themeContext?: ThemeContext,
) {
  if (themeContext) {
    await page.addInitScript(({ theme, mode }) => {
      localStorage.setItem('cameltv-theme-color', theme)
      localStorage.setItem('cameltv-theme-mode', mode)
    }, themeContext)
  }
  const probe = attachRuntimeProbe(page)
  const projectId = await login(page, probe)
  const loginRuntime = probe.snapshot()
  const loginIssues = [
    ...loginRuntime.consoleErrors.map(
      (error) => `console.error：${formatConsoleError(error)}`,
    ),
    ...loginRuntime.pageErrors.map((error) => `pageerror：${error}`),
    ...loginRuntime.failedRequests.map((error) => `请求传输失败：${error}`),
    ...loginRuntime.failedResponses.map(
      (error) => `API 错误响应：${formatFailedResponse(error)}`,
    ),
    ...loginRuntime.duplicateGets.map((error) => `重复有效 GET：${error}`),
  ]

  probe.reset()
  const fixtures = await createDynamicFixtures(page, projectId)
  let routeResults: RouteResult[] = []
  try {
    routeResults = await runRouteMatrix(
      page,
      testInfo,
      viewport,
      fixtures,
      probe,
      themeContext,
    )
  } finally {
    await cleanupDynamicFixtures(page, projectId, fixtures)
  }

  const routeFailures = routeResults
    .filter((result) => result.issues.length > 0)
    .map(
      (result) =>
        `[${result.viewport}] ${result.path}\n  - ${result.issues.join('\n  - ')}`,
    )
  const failures = [
    ...loginIssues.map((issue) => `[login] ${issue}`),
    ...routeFailures,
  ]
  expect(
    failures,
    `Batch57 ${viewport}${themeContext ? ` ${themeContext.theme}/${themeContext.mode}` : ''} 真实后端生产验收失败：\n${failures.join('\n')}`,
  ).toEqual([])
}

test.describe.serial('Batch 57 PC 真实后端生产验收', () => {
  test.beforeAll(() => {
    expect(
      credentials.username,
      '缺少 E2E_USERNAME：Batch56 生产验收禁止跳过凭据门禁',
    ).not.toBe('')
    expect(
      credentials.password,
      '缺少 E2E_PASSWORD：Batch56 生产验收禁止跳过凭据门禁',
    ).not.toBe('')
  })

  for (const themeContext of pcThemeModes) {
    test(`PC P0 ${themeContext.theme}/${themeContext.mode} 真实登录全路由生产矩阵`, async ({ page }, testInfo) => {
      test.setTimeout(660_000)
      await runAcceptanceViewport(page, testInfo, 'desktop', themeContext)
    })
  }

})

test.describe.serial('Batch 59 平板与移动端遗留验收', () => {
  test.beforeAll(() => {
    expect(
      credentials.username,
      '缺少 E2E_USERNAME：Batch59 平板/移动端验收禁止跳过凭据门禁',
    ).not.toBe('')
    expect(
      credentials.password,
      '缺少 E2E_PASSWORD：Batch59 平板/移动端验收禁止跳过凭据门禁',
    ).not.toBe('')
  })

  for (const viewport of ['tablet', 'mobile'] as const) {
    test(`${viewport} P0 obsidian-flow/dark 真实登录路由矩阵`, async ({ page }, testInfo) => {
      test.setTimeout(660_000)
      await runAcceptanceViewport(
        page,
        testInfo,
        viewport,
        { theme: 'obsidian-flow', mode: 'dark' },
      )
    })
  }
})
