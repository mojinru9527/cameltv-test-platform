import { expect, test, type Page, type Route } from '@playwright/test'

const PROJECT_A = { id: 61, code: 'batch61-a', name: 'Batch 61 项目 A' }
const PROJECT_B = { id: 62, code: 'batch61-b', name: 'Batch 61 项目 B' }
const EMPTY_PAGE = { total: 0, page: 1, page_size: 20, items: [] }

const ROUTES = [
  { route: '/requirement', api: '/requirements' },
  { route: '/testcase', api: '/test-cases' },
  { route: '/testplan', api: '/test-plans' },
  { route: '/report', api: '/reports' },
  { route: '/defect', api: '/defects' },
  { route: '/trace', api: '/trace/coverage' },
  { route: '/environment', api: '/environments' },
  { route: '/dataset', api: '/datasets' },
  { route: '/integration', api: '/integrations' },
  { route: '/uitest', api: '/ui-tests' },
] as const

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

function responseFor(apiPath: string, projectId: number) {
  if (apiPath === '/system/menus') return []
  if (apiPath === '/test-cases/domains') return []
  if (apiPath === '/reports/trends') {
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
  if (apiPath === '/defects/stats') return { total: 0, by_severity: {}, by_status: {} }
  if (apiPath === '/trace/coverage') {
    return {
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
    }
  }
  if (apiPath === '/environments') return []
  if (apiPath === '/integrations') return { items: [], total: 0 }
  if (apiPath === '/lanhu-evidence/jobs') return { ...EMPTY_PAGE, page_size: 50 }
  if (apiPath === '/ui-tests/scripts') return { available_specs: [] }
  if (apiPath === '/test-cases') {
    return {
      ...EMPTY_PAGE,
      total: 1,
      items: [{
        id: projectId * 100,
        title: projectId === PROJECT_A.id ? '项目 A 陈旧用例' : '项目 B 当前用例',
        domain: '隔离验收',
        module: '项目切换',
        priority: 'P0',
        review_status: 'draft',
      }],
    }
  }
  return EMPTY_PAGE
}

async function installProjectFixture(page: Page, requests: Array<{ path: string; projectId: number }>) {
  await page.addInitScript(({ projectA, projectB }) => {
    localStorage.setItem('cameltv-auth', JSON.stringify({
      state: {
        user: { id: 61, username: 'isolation-admin', nickname: 'Isolation Admin', email: '' },
        projects: [projectA, projectB],
        permissions: ['*'],
        currentProjectId: projectA.id,
        mustChangePassword: false,
        projectThemeMap: {},
      },
      version: 0,
    }))
  }, { projectA: PROJECT_A, projectB: PROJECT_B })

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const apiPath = url.pathname.replace(/^\/api\/v1/, '')
    const projectId = Number(request.headers()['x-project-id'] || PROJECT_A.id)
    if (request.method() !== 'GET') return route.abort('blockedbyclient')
    requests.push({ path: apiPath, projectId })
    return ok(route, responseFor(apiPath, projectId))
  })
}

async function switchToProjectB(page: Page) {
  await page.getByRole('combobox', { name: '当前项目' }).click()
  await page.getByRole('option', { name: PROJECT_B.name }).click()
  await expect(page.locator(`[data-project-scope="${PROJECT_B.id}"]`)).toHaveCount(1)
  await expect(page.locator(`[data-project-scope="${PROJECT_A.id}"]`)).toHaveCount(0)
}

test.describe('Batch 61 project A to B route matrix', () => {
  for (const row of ROUTES) {
    test(`${row.route}: switch issues exactly one effective B list GET`, async ({ page }) => {
      const requests: Array<{ path: string; projectId: number }> = []
      await installProjectFixture(page, requests)
      await page.goto(row.route)
      await expect.poll(() => requests.filter(
        (request) => request.path === row.api && request.projectId === PROJECT_A.id,
      ).length).toBe(1)

      await switchToProjectB(page)

      await expect.poll(() => requests.filter(
        (request) => request.path === row.api && request.projectId === PROJECT_B.id,
      ).length).toBe(1)
    })
  }

  test('testcase switch removes A rows and renders only B rows', async ({ page }) => {
    const requests: Array<{ path: string; projectId: number }> = []
    await installProjectFixture(page, requests)
    await page.goto('/testcase')
    await expect(page.getByText('项目 A 陈旧用例')).toBeVisible()

    await switchToProjectB(page)

    await expect(page.getByText('项目 B 当前用例')).toBeVisible()
    await expect(page.getByText('项目 A 陈旧用例')).toHaveCount(0)
  })
})
