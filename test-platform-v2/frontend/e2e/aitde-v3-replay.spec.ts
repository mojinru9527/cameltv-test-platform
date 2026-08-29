/**
 * AITDE V3 执行回放冒烟 — Run 详情 + Replay manifest（V3.1 Proof Replay，C1）。
 *
 * 前置条件见 e2e/helpers/aitde.ts；需存在可访问的统一 Run（run 1 由
 * shadow_compare_legacy_runs.py 真实执行产生；无数据时本 spec skip）。
 */
import { expect, test } from '@playwright/test'
import { HAS_AUTH, loginAndPickProject } from './helpers/aitde'

// 通过后端 API 探测一个可用的 run id；探测不到则整组 skip
async function firstRunId(): Promise<number | null> {
  const base = process.env.BASE_URL || 'http://localhost:5441'
  try {
    const login = await fetch(`${base}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: process.env.E2E_USERNAME || '',
        password: process.env.E2E_PASSWORD || '',
      }),
    })
    const { data } = await login.json()
    const run = await fetch(`${base}/api/v2/runs/1`, {
      headers: { Authorization: `Bearer ${data.access_token}`, 'X-Project-Id': '1' },
    })
    const body = await run.json()
    return body?.data?.id ?? null
  } catch {
    return null
  }
}

let runId: number | null = null

test.describe('AITDE V3 回放冒烟', () => {
  test.beforeAll(async () => {
    runId = await firstRunId()
  })

  test.beforeEach(async ({ page }) => {
    test.skip(!HAS_AUTH, '未通过环境变量授权 E2E 登录账号')
    test.skip(runId === null, '无可用统一 Run（先运行 shadow_compare_legacy_runs.py）')
    await loginAndPickProject(page)
  })

  test('Run 详情页渲染统一结论', async ({ page }) => {
    await page.goto(`/executions/${runId}`)
    await expect(page.getByRole('heading', { name: `Run #${runId}` })).toBeVisible({
      timeout: 15_000,
    })
    // 统一结论徽章（OutcomeBadge 中文标签）渲染
    await expect(page.getByText(/通过|业务失败|无法判定|环境失败|执行失败/).first()).toBeVisible()
  })

  test('Replay 页渲染 manifest 时间线与证据', async ({ page }) => {
    await page.goto(`/executions/${runId}/replay`)
    await expect(page.getByRole('heading', { name: `回放 Run #${runId}` })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByText('时间线')).toBeVisible()
  })
})
