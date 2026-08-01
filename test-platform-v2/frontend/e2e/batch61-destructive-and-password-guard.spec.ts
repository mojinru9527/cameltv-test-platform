import { expect, test, type Page, type Route } from '@playwright/test'

function reply(route: Route, status: number, code: number, msg: string, data: unknown) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify({ code, msg, data }),
  })
}

async function seedAuth(page: Page, mustChangePassword = false) {
  await page.addInitScript(({ forced }) => {
    localStorage.setItem('cameltv-auth', JSON.stringify({
      state: {
        user: { id: 61, username: 'batch61-guard', nickname: 'Batch 61 Guard', email: '' },
        projects: [{ id: 62, code: 'batch61-b', name: 'Batch 61 项目 B' }],
        permissions: ['*'],
        currentProjectId: 62,
        mustChangePassword: forced,
        projectThemeMap: {},
      },
      version: 0,
    }))
  }, { forced: mustChangePassword })
}

function testcasePage() {
  return {
    total: 2,
    page: 1,
    page_size: 20,
    items: [
      { id: 6201, title: '删除保护用例 A', module: '保护', priority: 'P0', review_status: 'draft' },
      { id: 6202, title: '删除保护用例 B', module: '保护', priority: 'P1', review_status: 'draft' },
    ],
  }
}

test('batch delete cancel is zero-write and repeated confirmation is one atomic B write', async ({ page }) => {
  await seedAuth(page)
  let deleteWrites = 0
  let deleteProject = ''
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'GET' && path === '/system/menus') return reply(route, 200, 0, 'ok', [])
    if (request.method() === 'GET' && path === '/test-cases/domains') return reply(route, 200, 0, 'ok', [])
    if (request.method() === 'GET' && path === '/test-cases') return reply(route, 200, 0, 'ok', testcasePage())
    if (request.method() === 'DELETE' && path === '/test-cases/batch') {
      deleteWrites += 1
      deleteProject = request.headers()['x-project-id'] || ''
      await new Promise((resolve) => setTimeout(resolve, 200))
      return reply(route, 200, 0, 'ok', { deleted: 2, atomic: true })
    }
    return reply(route, 404, 404, 'not found', null)
  })

  await page.goto('/testcase')
  await page.getByRole('checkbox', { name: '选择当前页全部用例' }).click()
  await page.getByRole('button', { name: '批量删除 (2)' }).click()
  await expect(page.getByRole('alertdialog').getByText(/Batch 61 项目 B/)).toBeVisible()
  await page.getByRole('button', { name: '取消', exact: true }).click()
  expect(deleteWrites).toBe(0)

  await page.getByRole('button', { name: '批量删除 (2)' }).click()
  const confirm = page.getByRole('button', { name: '确认删除' })
  await confirm.evaluate((button) => {
    ;(button as HTMLButtonElement).click()
    ;(button as HTMLButtonElement).click()
  })
  await expect.poll(() => deleteWrites).toBe(1)
  await expect(page.getByRole('heading', { name: '确认批量删除用例？' })).toHaveCount(0)
  expect(deleteProject).toBe('62')
})

test('atomic delete failure keeps the reviewed scope open and never reports success', async ({ page }) => {
  await seedAuth(page)
  let deleteWrites = 0
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'GET' && path === '/system/menus') return reply(route, 200, 0, 'ok', [])
    if (request.method() === 'GET' && path === '/test-cases/domains') return reply(route, 200, 0, 'ok', [])
    if (request.method() === 'GET' && path === '/test-cases') return reply(route, 200, 0, 'ok', testcasePage())
    if (request.method() === 'DELETE' && path === '/test-cases/batch') {
      deleteWrites += 1
      return reply(route, 409, 409, 'atomic rollback', null)
    }
    return reply(route, 404, 404, 'not found', null)
  })

  await page.goto('/testcase')
  await page.getByRole('checkbox', { name: '选择当前页全部用例' }).click()
  await page.getByRole('button', { name: '批量删除 (2)' }).click()
  await page.getByRole('button', { name: '确认删除' }).click()

  await expect.poll(() => deleteWrites).toBe(1)
  await expect(page.getByRole('heading', { name: '确认批量删除用例？' })).toBeVisible()
  await expect(page.getByText(/2 条用例/)).toBeVisible()
})

test('forced-password user cannot bypass the change-password route and weak input creates zero writes', async ({ page }) => {
  await seedAuth(page, true)
  let passwordWrites = 0
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'POST' && path === '/auth/change-password') passwordWrites += 1
    return reply(route, 200, 0, 'ok', null)
  })

  await page.goto('/testcase')
  await expect(page).toHaveURL(/\/change-password$/)
  await expect(page.getByRole('heading', { name: '首次登录，请修改密码' })).toBeVisible()
  await expect(page.getByRole('button')).toHaveCount(2)

  await page.getByLabel('原密码').fill('OldPass1')
  await page.getByLabel('新密码', { exact: true }).fill('123')
  await page.getByLabel('确认新密码').fill('123')
  await page.getByRole('button', { name: '修改密码' }).click()

  await expect(page.getByRole('alert')).toContainText('至少 6 位')
  expect(passwordWrites).toBe(0)
})

test('successful forced password change logs out the old browser session', async ({ page }) => {
  await seedAuth(page, true)
  const calls: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'POST') calls.push(path)
    return reply(route, 200, 0, 'ok', null)
  })

  await page.goto('/change-password')
  await page.getByLabel('原密码').fill('OldPass1')
  await page.getByLabel('新密码', { exact: true }).fill('NewPass2')
  await page.getByLabel('确认新密码').fill('NewPass2')
  await page.getByRole('button', { name: '修改密码' }).click()

  await expect(page).toHaveURL(/\/login$/)
  expect(calls).toEqual(['/auth/change-password', '/auth/logout'])
  const persisted = await page.evaluate(() => JSON.parse(localStorage.getItem('cameltv-auth') || '{}'))
  expect(persisted.state.user).toBeNull()
  expect(persisted.state.mustChangePassword).toBe(false)
})
