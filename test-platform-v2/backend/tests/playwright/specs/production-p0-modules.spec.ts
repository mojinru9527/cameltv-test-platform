import { expect, test, type Page } from '@playwright/test'

import {
  assertP0RequestAllowed,
  readP0Runtime,
  type P0Runtime,
} from '../support/production-p0-contract'

const API_URL_PATTERN = /api\./i

async function guardP0(page: Page, runtime: P0Runtime): Promise<string[]> {
  const rejected: string[] = []
  await page.route('**/*', async (route) => {
    const request = route.request()
    try {
      assertP0RequestAllowed(runtime, request.url(), request.method())
      await route.continue()
      return
    } catch (error) {
      rejected.push(error instanceof Error ? error.message : String(error))
      await route.abort('blockedbyclient')
    }
  })
  return rejected
}

function apiObservations(page: Page): string[] {
  const urls: string[] = []
  page.on('response', (response) => {
    if (API_URL_PATTERN.test(response.url())) {
      urls.push(response.url())
    }
  })
  return urls
}

test.describe('体育平台 生产 P0 功能用例 → UI 自动化（只读）', () => {
  let runtime: P0Runtime

  test.beforeAll(() => {
    runtime = readP0Runtime()
  })

  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(20_000)
    page.setDefaultNavigationTimeout(30_000)
  })

  test.afterEach(async ({ page }, testInfo) => {
    const dir = process.env.P0_EVIDENCE_DIR || 'p0-evidence'
    await page
      .screenshot({
        path: `${dir}/${testInfo.title.replace(/[^\w\u4e00-\u9fa5-]/g, '_').slice(0, 80)}.png`,
        fullPage: false,
      })
      .catch(() => undefined)
  })

  test('P0-UI-001 首页：Live Matches/搜索/REGISTER + 核心 API 资产', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    const apiUrls = apiObservations(page)
    const response = await page.goto(runtime.baseUrl.toString(), { waitUntil: 'networkidle' })
    expect(response?.status() ?? 0).toBeGreaterThanOrEqual(200)
    await expect(page.getByText(/Live Matches|Favorites|Competitions/i).first()).toBeVisible()
    await expect(page.locator('input[type="text"], input[type="search"]').first()).toBeVisible()
    await expect(page.getByText(/REGISTER|Register/i).first()).toBeVisible()
    expect(apiUrls.some((u) => /ads\/activity|search\/hot|client\/general/i.test(u))).toBe(true)
    expect(rejected).toEqual([])
  })

  test('P0-UI-002 赛事详情：标题/比分/标签渲染', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/football/as-monaco-vs-getafe/n54qllhn0vwjqvy', runtime.baseUrl).toString(), {
      waitUntil: 'domcontentloaded',
    })
    await expect(page.getByText(/AS Monaco|Getafe|Monaco/i).first()).toBeVisible()
    const headings = await page.locator('h1,h2,h3').allTextContents()
    expect(headings.join(' ').length).toBeGreaterThan(10)
    expect(rejected).toEqual([])
  })

  test('P0-UI-003 直播间：视频容器/直播页面渲染', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/football/persatuan-sepakbola-indonesia-jakarta-vs-arema-fc/live/2y8m4zh5kwgpql0', runtime.baseUrl).toString(), {
      waitUntil: 'domcontentloaded',
    })
    await expect(page.locator('[class*="roomLive"]').first()).toBeVisible()
    await expect(page.getByText(/Live Streaming|Live Score/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('P0-UI-004 资讯：列表 + 首条资讯详情可达', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/q/news', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    const articleLinks = page.locator('a[href*="/news/detail/"]')
    await expect(articleLinks.first()).toBeVisible()
    const href = await articleLinks.first().getAttribute('href')
    expect(href).toBeTruthy()
    expect(rejected).toEqual([])
  })

  test('P0-UI-005 搜索：输入查询并看到结果（查询型 POST 放行）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/search', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    const input = page.locator('input[type="text"], input[type="search"]').first()
    await expect(input).toBeVisible()
    await input.fill('Real Madrid')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(2500)
    const bodyText = await page.locator('body').innerText()
    expect(/Real Madrid|real madrid/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('P0-UI-006 我的：Login 引导 + 资产/功能入口渲染', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/my', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    await expect(page.getByText(/Login|登录/i).first()).toBeVisible()
    await expect(page.getByText(/Silver Diamond|Camel Mall|Favorites|Outfits|FAQ/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('P0-UI-007 联赛：积分榜/赛程表面渲染', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/r/league/UEFA%20Europa%20League', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    await expect(page.getByText(/UEFA Europa League/i).first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/Standings|Schedule|Fixture/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('P0-UI-008 回放：列表渲染记录', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/match-replay', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    const replayLinks = page.locator('a[href*="/match-replay/"]')
    await expect(replayLinks.first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('P0-UI-009 世界杯：Match Center/Schedule/Groups/Bracket 表面', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/worldcup-2026', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    await expect(page.getByText(/World Cup 2026|FIFA World Cup/i).first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/Match Center|Schedule|Groups|Bracket/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('P0-UI-010 首页加载性能：15s 内完成', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    const startedAt = Date.now()
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'load' })
    expect(Date.now() - startedAt).toBeLessThan(15_000)
    expect(rejected).toEqual([])
  })
})
