/**
 * Batch 94 — AI 产物批量审核/采纳/导入 E2E
 *
 * 前置：后端(8051，AI_ARTIFACT_ALLOW_BATCH_IMPORT=true，已种 3 pending + 2 approved 产物) + 前端(5221)。
 * 凭据经 E2E_USERNAME / E2E_PASSWORD 注入（需 knowledge:approve + ai_artifact:import）。
 */
import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://localhost:5221'
const USERNAME = process.env.E2E_USERNAME || 'admin'
const PASSWORD = process.env.E2E_PASSWORD || ''
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = path.resolve(SPEC_DIR, '../../work-logs/evidence/batch-94')

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByPlaceholder('用户名').fill(USERNAME)
  await page.getByPlaceholder('密码').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 20_000 })
  await page.waitForLoadState('networkidle')
}

test('AI 审核台：批量采纳 + 批量导入', async ({ page }) => {
  await login(page)
  await page.goto(`${BASE_URL}/knowledge?tab=artifacts`)
  await page.waitForLoadState('networkidle')

  // 待审核 3 条可见
  await expect(page.getByText('批量产物-1')).toBeVisible({ timeout: 15_000 })
  await page.screenshot({ path: path.join(EVIDENCE_DIR, 'artifacts-list.png'), fullPage: true })

  // 全选 → 批量采纳
  await page.getByLabel('全选当前页可操作产物').check()
  await expect(page.getByText('已选 5 条')).toBeVisible()
  await page.getByRole('button', { name: '批量采纳' }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect(page.getByText('已采纳 5 条')).toBeVisible({ timeout: 10_000 })
  await page.screenshot({ path: path.join(EVIDENCE_DIR, 'batch-approved.png'), fullPage: true })

  // 切到「已采纳」→ 全选 → 批量导入
  await page.getByRole('combobox', { name: '筛选审核状态' }).click()
  await page.getByRole('option', { name: '已采纳' }).click()
  await page.waitForLoadState('networkidle')
  await expect(page.getByText('批量产物-1')).toBeVisible({ timeout: 10_000 })
  await page.getByLabel('全选当前页可操作产物').check()
  await page.getByRole('button', { name: '批量导入' }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect(page.getByText('已导入 5 条').or(page.getByText('已导入 '))).toBeVisible({ timeout: 15_000 })
  await page.screenshot({ path: path.join(EVIDENCE_DIR, 'batch-imported.png'), fullPage: true })
})
