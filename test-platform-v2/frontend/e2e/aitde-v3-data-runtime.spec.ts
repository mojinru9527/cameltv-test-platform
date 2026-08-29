/**
 * AITDE V3 数据运行时冒烟 — 数据源 + Fixture 页面可达（V3.2 Data Runtime，C1）。
 *
 * 前置条件见 e2e/helpers/aitde.ts。空态也视为通过（冒烟目标是链路可达与
 * 前后端契约一致，而非数据存在）。
 */
import { expect, test } from '@playwright/test'
import { HAS_AUTH, loginAndPickProject } from './helpers/aitde'

test.describe('AITDE V3 数据运行时冒烟', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!HAS_AUTH, '未通过环境变量授权 E2E 登录账号')
    await loginAndPickProject(page)
  })

  test('数据源页面渲染（列表或空态）', async ({ page }) => {
    await page.goto('/data-sources')
    const table = page.locator('table')
    const empty = page.getByText('暂无数据源')
    await expect(table.or(empty).first()).toBeVisible({ timeout: 15_000 })
  })

  test('Fixture 页面渲染（ID 查询入口 + 说明卡片）', async ({ page }) => {
    await page.goto('/fixtures')
    await expect(page.getByText('输入 Fixture ID')).toBeVisible({ timeout: 15_000 })
  })
})
