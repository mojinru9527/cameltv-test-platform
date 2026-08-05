/**
 * Batch 92 — 蓝湖证据包 UI 冒烟（C55/C87 证据包工作流前端化）
 *
 * 前置：后端(8049) + 前端(5219) 已启动；凭据经 E2E_USERNAME / E2E_PASSWORD 注入（需 lanhu_evidence:view/run/review/import）。
 */
import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://localhost:5219'
const USERNAME = process.env.E2E_USERNAME || 'admin'
const PASSWORD = process.env.E2E_PASSWORD || ''
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = path.resolve(SPEC_DIR, '../../work-logs/evidence/batch-92')
const LANHU_URL =
  'https://lanhuapp.com/web/#/item/project/stage?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1&pid=c92eba63-69eb-4123-97c0-6605ce2e3216'

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByPlaceholder('用户名').fill(USERNAME)
  await page.getByPlaceholder('密码').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 20_000 })
  await page.waitForLoadState('networkidle')
}

test('蓝湖证据包：菜单/列表/新建/详情', async ({ page }) => {
  await login(page)

  // 侧边栏菜单可见
  await expect(page.getByText('蓝湖证据包', { exact: true }).first()).toBeVisible({ timeout: 10_000 })
  await page.goto(`${BASE_URL}/lanhu-evidence`)
  await page.waitForLoadState('networkidle')
  await expect(page.getByRole('heading', { name: '蓝湖证据包' })).toBeVisible()
  await page.screenshot({ path: path.join(EVIDENCE_DIR, 'list-empty.png'), fullPage: true })

  // 新建任务
  await page.getByRole('button', { name: '新建采集任务' }).first().click()
  await page.getByPlaceholder(/lanhuapp\.com/).fill(LANHU_URL)
  await page.getByRole('button', { name: '创建任务' }).click()
  await expect(page.getByText('证据包任务已创建')).toBeVisible({ timeout: 10_000 })

  // 列表出现任务行
  const row = page.locator('tbody tr').first()
  await expect(row).toBeVisible({ timeout: 10_000 })
  await page.screenshot({ path: path.join(EVIDENCE_DIR, 'list-created.png'), fullPage: true })

  // 打开详情
  await page.getByRole('button', { name: /查看任务 \d+ 详情/ }).first().click()
  await page.waitForURL(/\/lanhu-evidence\/\d+/, { timeout: 10_000 })
  await page.waitForLoadState('networkidle')
  await expect(page.getByText('证据包任务 #')).toBeVisible()
  await page.screenshot({ path: path.join(EVIDENCE_DIR, 'detail.png'), fullPage: true })

  // 权限按钮（admin 应见「导入」与「审核」入口；任务若仍采集中则不显示导入）
  const importBtn = page.getByRole('button', { name: '导入' })
  if (await importBtn.count()) {
    await importBtn.first().click()
    await expect(page.getByText('导入证据包')).toBeVisible()
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'import-dialog.png'), fullPage: true })
    await page.getByRole('button', { name: '取消' }).first().click()
  }
})
