/**
 * AITDE V3 主链冒烟 — /missions 列表 → 新建 Mission → 概览（V3.0 主链，C1）。
 *
 * 前置条件见 e2e/helpers/aitde.ts；AITDE_V3_ENABLED 需在前后端同时开启。
 */
import { expect, test } from '@playwright/test'
import { HAS_AUTH, loginAndPickProject } from './helpers/aitde'

test.describe('AITDE V3 主链冒烟', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!HAS_AUTH, '未通过环境变量授权 E2E 登录账号')
    await loginAndPickProject(page)
  })

  test('missions 列表页渲染（菜单入口 V30-103）', async ({ page }) => {
    await page.goto('/missions')
    await expect(page.getByRole('heading', { name: '测试任务' })).toBeVisible()
    await expect(page.getByRole('button', { name: '新建 Mission' })).toBeVisible()
    // 列表或空态二者其一必须渲染（不允许白屏/权限 404）
    const table = page.locator('table')
    const empty = page.getByText('暂无测试任务')
    await expect(table.or(empty).first()).toBeVisible({ timeout: 15_000 })
  })

  test('新建 Mission 两步提交 → 跳转概览', async ({ page }) => {
    await page.goto('/missions')
    await page.getByRole('button', { name: '新建 Mission' }).click()
    await expect(page).toHaveURL(/\/missions\/new/)

    const title = `E2E 冒烟任务 ${Date.now()}`
    await page.fill('#mission-title', title)
    await page.getByRole('button', { name: '下一步' }).click()
    await expect(page.getByText(/任务名称：/)).toBeVisible()
    await page.getByRole('button', { name: '创建任务' }).click()

    await expect(page).toHaveURL(/\/missions\/\d+\/overview/, { timeout: 15_000 })
    await expect(page.getByText('Mission 主链')).toBeVisible()
  })

  test('概览页 AI 调试入口按权限渲染（V30-085）', async ({ page }) => {
    await page.goto('/missions')
    // 打开第一个任务行（键盘可达：Enter）
    await page.getByLabel(/打开测试任务/).first().click()
    await expect(page).toHaveURL(/\/missions\/\d+\/overview/, { timeout: 15_000 })
    await expect(page.getByText('Mission 主链')).toBeVisible()
    await expect(page.getByRole('button', { name: '查看 AI 调试信息' })).toBeVisible()
  })
})
