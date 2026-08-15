import { expect, test, type Page } from '@playwright/test'

import {
  assertP0RequestAllowed,
  readP0Runtime,
  type P0Runtime,
} from '../support/production-p0-contract'

const SITE_HOSTS = new Set(['www.camel1.tv', 'camel1.tv', 'www.cameltv.live', 'cameltv.live', 'www.camel1.to', 'camel1.to'])
const MATCH_URL = '/football/as-monaco-vs-getafe/n54qllhn0vwjqvy'
const TEAM_FALLBACK = '/team/Chelsea/j1l4rjnhpdxm7vx'
const PLAYER_FALLBACK = '/player/Martin%20Odegaard/4wyrn4hdjonq86p'

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

async function stayOnSite(page: Page): Promise<void> {
  const host = new URL(page.url()).hostname.toLowerCase()
  expect(SITE_HOSTS.has(host), `页面被劫持到非站点主机: ${host}`).toBe(true)
}

async function openFirstLink(page: Page, runtime: P0Runtime, hrefPart: string, fallback: string): Promise<void> {
  const link = page.locator(`a[href*="${hrefPart}"]`).first()
  if (await link.count()) {
    const href = await link.getAttribute('href')
    expect(href).toContain(hrefPart)
    await link.click()
    try {
      await page.waitForURL(new RegExp(hrefPart.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), { timeout: 12_000 })
    } catch {
      await page.goto(new URL(fallback, runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    }
  } else {
    await page.goto(new URL(fallback, runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  }
}

test.describe('体育平台 生产 P0 补充用例 → UI 自动化（只读，Batch 187）', () => {
  test.describe.configure({ retries: 1 })
  let runtime: P0Runtime

  test.beforeAll(() => {
    runtime = readP0Runtime()
  })

  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(20_000)
    page.setDefaultNavigationTimeout(30_000)
    expect.configure({ timeout: 15_000 })
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

  test('SUPP-001 登录/注册入口：REGISTER 按钮 + 我的页登录引导（M5 P0）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'networkidle' })
    const register = page.getByText(/REGISTER/i).first()
    await expect(register).toBeVisible()
    await register.click({ force: true })
    await page.waitForTimeout(1500)
    await stayOnSite(page)
    await page.goto(new URL('/my', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Login|登录/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('SUPP-002 预测交互：赛事详情预测区 + 预测列表页（M7 P0）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL(MATCH_URL, runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Prediction/i).first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/1X2|Home Win|Draw|Away Win|Odds/i.test(bodyText)).toBe(true)
    await page.goto(new URL('/prediction/more', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    await expect(page.getByText(/Match Prediction/i).first()).toBeVisible()
    await expect(page.getByText(/\bVS\b/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('SUPP-003 银钻/商城入口：我的页资产入口渲染（M5）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/my', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Silver Diamond/i).first()).toBeVisible()
    await expect(page.getByText(/Free Silver Diamond/i).first()).toBeVisible()
    await expect(page.getByText(/Camel Mall/i).first()).toBeVisible()
    await expect(page.getByText(/My Favorites/i).first()).toBeVisible()
    await expect(page.getByText(/My Outfits/i).first()).toBeVisible()
    await expect(page.getByText(/FAQ & Feedback/i).first()).toBeVisible()
    await expect(page.getByText(/Settings/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('SUPP-004 广告弹窗处理：首页加载不跳离站点、无第三方弹窗残留（M8 P0）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    const popups: string[] = []
    page.on('popup', (p) => {
      popups.push(p.url())
      p.close().catch(() => undefined)
    })
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'networkidle' })
    await page.waitForTimeout(2500)
    await stayOnSite(page)
    await expect(page.getByText(/Live Matches|Favorites|Competitions/i).first()).toBeVisible()
    expect(popups.length).toBe(0)
    expect(rejected).toEqual([])
  })

  test('SUPP-005 搜索分类：ALL/MATCH/TEAM/PLAYER/NEWS 分类渲染（M6）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/search#q=Real%20Madrid&f=home', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    for (const tab of ['ALL', 'MATCH', 'TEAM', 'PLAYER', 'NEWS']) {
      await expect(page.getByText(new RegExp(`^${tab}$`)).first()).toBeVisible()
    }
    await expect(page.locator('a[href*="/team/"]').first()).toBeVisible()
    await expect(page.locator('a[href*="/player/"]').first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/News/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('SUPP-006 球队详情：积分榜/近期战绩/基本信息渲染（M3）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'domcontentloaded' })
    await openFirstLink(page, runtime, '/team/', TEAM_FALLBACK)
    await expect(page.locator('h1,h2').first()).toBeVisible()
    await page.waitForTimeout(1500)
    const bodyText = await page.locator('body').innerText()
    expect(/Standings|Basic Information|Last 5 Matches|Info/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('SUPP-007 球员详情：资料/身价/转会史渲染（M3）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/search#q=Real%20Madrid&f=home', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
    await openFirstLink(page, runtime, '/player/', PLAYER_FALLBACK)
    await expect(page.locator('h1,h2').first()).toBeVisible()
    await page.waitForTimeout(1500)
    const bodyText = await page.locator('body').innerText()
    expect(/Transfer History|YRS|Contract|Age/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('SUPP-008 反馈表单：字段渲染 + 500 字计数（M9，不提交）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/my/feedback', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Issue Type/i).first()).toBeVisible()
    for (const opt of ['Lag', 'Page Optimization', 'Unable to Connect', 'Data Error', 'Account-Related']) {
      await expect(page.getByText(new RegExp(opt)).first()).toBeVisible()
    }
    await expect(page.getByText(/Feedback Content/i).first()).toBeVisible()
    await expect(page.getByText(/0\/500/i).first()).toBeVisible()
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible()
    await textarea.fill('x'.repeat(20))
    await expect(page.getByText(/20\/500/i).first()).toBeVisible()
    await expect(page.getByText(/Contact Information \(Optional\)/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('SUPP-009 16.0.0 体育项目 TAB：Football/Basketball 切换（P0，TAB 未上线则跳过）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)
    const basketballTab = page.getByText(/^Basketball$/i)
    if ((await basketballTab.count()) === 0) {
      test.skip(true, '16.0.0 Basketball TAB 尚未上线，跳过')
      return
    }
    await basketballTab.first().click()
    await page.waitForTimeout(2500)
    await stayOnSite(page)
    await expect(page.getByText(/^Basketball$/i).first()).toBeVisible()
    const footballTab = page.getByText(/^Football$/i).first()
    await expect(footballTab).toBeVisible()
    await footballTab.click()
    await page.waitForTimeout(2500)
    await stayOnSite(page)
    await expect(page.getByText(/Live Matches|Favorites|Competitions/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('SUPP-010 FAQ：问题列表 + 详情可达 + Load More（M9）', async ({ page }) => {
    const rejected = await guardP0(page, runtime)
    await page.goto(new URL('/my/faq', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
    await expect(page.locator('a[href*="/my/faq/"]').first()).toBeVisible()
    await expect(page.getByText(/Load More/i).first()).toBeVisible()
    await expect(page.getByText(/FAQ & Feedback/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })
})
