import { expect, test, type Page, type Route } from '@playwright/test'

type RoleFixture = {
  role: 'admin' | 'tester' | 'viewer'
  permissions: string[]
  canCreate: boolean
  canUpdate: boolean
  canDelete: boolean
}

const ROLES: RoleFixture[] = [
  { role: 'admin', permissions: ['*'], canCreate: true, canUpdate: true, canDelete: true },
  {
    role: 'tester',
    permissions: ['testcase:list', 'testcase:detail', 'testcase:create', 'testcase:update'],
    canCreate: true,
    canUpdate: true,
    canDelete: false,
  },
  {
    role: 'viewer',
    permissions: ['testcase:list', 'testcase:detail'],
    canCreate: false,
    canUpdate: false,
    canDelete: false,
  },
]

function envelope(route: Route, status: number, code: number, msg: string, data: unknown) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify({ code, msg, data }),
  })
}

function hasPermission(role: RoleFixture, permission: string) {
  return role.permissions.includes('*') || role.permissions.includes(permission)
}

async function installRoleFixture(page: Page, role: RoleFixture) {
  await page.addInitScript(({ roleName, permissions }) => {
    localStorage.setItem('cameltv-auth', JSON.stringify({
      state: {
        user: { id: 61, username: roleName, nickname: roleName, email: '' },
        projects: [{ id: 61, code: 'batch61', name: 'Batch 61 RBAC 项目' }],
        permissions,
        currentProjectId: 61,
        mustChangePassword: false,
        projectThemeMap: {},
      },
      version: 0,
    }))
  }, { roleName: role.role, permissions: role.permissions })

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() === 'GET' && path === '/system/menus') return envelope(route, 200, 0, 'ok', [])
    if (request.method() === 'GET' && path === '/test-cases/domains') return envelope(route, 200, 0, 'ok', [])
    if (request.method() === 'GET' && path === '/test-cases') {
      return envelope(route, 200, 0, 'ok', {
        total: 1,
        page: 1,
        page_size: 20,
        items: [{
          id: 6101,
          title: 'RBAC 生产用例',
          domain: '权限',
          module: '角色矩阵',
          priority: 'P0',
          review_status: 'draft',
        }],
      })
    }
    if (request.method() === 'POST' && path === '/test-cases') {
      return hasPermission(role, 'testcase:create')
        ? envelope(route, 200, 0, 'ok', { id: 6102 })
        : envelope(route, 403, 403, '缺少权限 testcase:create', null)
    }
    if (request.method() === 'PUT' && path === '/test-cases/6101') {
      return hasPermission(role, 'testcase:update')
        ? envelope(route, 200, 0, 'ok', { id: 6101 })
        : envelope(route, 403, 403, '缺少权限 testcase:update', null)
    }
    if (request.method() === 'DELETE' && path === '/test-cases/6101') {
      return hasPermission(role, 'testcase:delete')
        ? envelope(route, 200, 0, 'ok', { deleted: true })
        : envelope(route, 403, 403, '缺少权限 testcase:delete', null)
    }
    return envelope(route, 404, 404, 'fixture route not found', null)
  })
}

test.describe('Batch 61 admin/tester/viewer capability matrix', () => {
  for (const role of ROLES) {
    test(`${role.role}: controls match backend action permissions`, async ({ page }) => {
      await installRoleFixture(page, role)
      await page.goto('/testcase')
      await expect(page.getByText('RBAC 生产用例')).toBeVisible()

      await expect(page.getByRole('button', { name: '新建用例' })).toHaveCount(role.canCreate ? 1 : 0)
      await expect(page.getByRole('button', { name: '编辑用例：RBAC 生产用例' })).toHaveCount(role.canUpdate ? 1 : 0)
      await expect(page.getByRole('button', { name: '删除用例：RBAC 生产用例' })).toHaveCount(role.canDelete ? 1 : 0)
      await expect(page.getByRole('checkbox', { name: '选择用例：RBAC 生产用例' })).toHaveCount(
        role.canUpdate || role.canDelete ? 1 : 0,
      )

      const statuses = await page.evaluate(async () => {
        const requests = [
          fetch('/api/v1/test-cases', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }),
          fetch('/api/v1/test-cases/6101', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: '{}' }),
          fetch('/api/v1/test-cases/6101', { method: 'DELETE' }),
        ]
        return Promise.all(requests).then((responses) => responses.map((response) => response.status))
      })

      expect(statuses).toEqual([
        role.canCreate ? 200 : 403,
        role.canUpdate ? 200 : 403,
        role.canDelete ? 200 : 403,
      ])
    })
  }
})
