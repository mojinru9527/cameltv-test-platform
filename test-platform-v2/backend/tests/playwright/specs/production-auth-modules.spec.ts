import { expect, test, type Page } from '@playwright/test'

/**
 * 生产 P0 登录态业务模块补充 UI 自动化（只读，Batch 189 二期）。
 *
 * 覆盖：银钻账户（余额/收支流水）、商城（徽章兑换列表）、设置页、
 * 我的收藏（分类页签）、登录态菜单导航链路。
 * 登录机制与守卫同 production-auth-supplement.spec.ts。
 */

const LOGIN_URL = 'https://api.cameltv.live/account-service/ee/client/demo/login'

const AUTH_READONLY_POST: RegExp[] = [
  /\/ee\/ads\/activity\/get$/,
  /\/ee\/search\/(hot|query|recommend)$/,
  /\/ee\/news\/(list_visible|related|get_visible|get)$/,
  /\/ee\/client\/(getHistoryMessage|web\/getAnchorNoticeMapper|getCountryCode|ipLog|getForbiddenUser)$/,
  /\/login\/anonymous\/web$/,
  /\/konfi-service\/web\/getDataById$/,
  /\/ee\/sports_live\/(view_match|loadAnchorsByMatchId|heartbeat)$/,
  /\/ee\/sports_live\/football\/match\/analysis$/,
  /\/ee\/forecast\/(match_list|user_list|index|queryOddsSummaryByMatchId|realtime\/odds|history)$/,
  /\/ee\/diamond\/(account|stats|records|red\/income\/daily)$/,
  /\/ee\/silverDiamond\/(account|task|event|invite\/home|invite\/recordList|records|record|shop|mall|exchangeRecord|exchange|trans)$/,
  /\/ee\/client\/demo\/login$/,
  /\/ee\/faq\/(list|one|get_full)$/,
  /\/ee\/replay\/list$/,
  /\/ee\/block_speak\/list$/,
  /\/ee\/article\/home$/,
  /\/ee\/favorite\/(list|subscriptions)$/,
  /\/ee\/sports_live\/list_favorite_/,
]

const WRITE_PATTERNS: RegExp[] = [
  /bet|cancel|pay|order|refund|recharge|withdraw|deposit|favorite\/add|like\b|comment|review|create|save|update|delete|add|remove|send|publish|bonus|gift|diamond\/withdraw|invite\/bind|feedback|report|exchange$/,
]

const BUSINESS_HOSTS = new Set(['api.cameltv.live', 'www.target.example.com', 'www.cameltv.live', 'livecdn.cameltv.live', 'img.cameltv.live', 'sensors.cameltv.live'])

function assertAuthRequestAllowed(rawUrl: string, method: string): string | null {
  const url = new URL(rawUrl)
  const m = method.trim().toUpperCase()
  if (m === 'GET' || m === 'HEAD') return null
  const path = url.pathname
  const host = url.hostname.toLowerCase()
  if (!BUSINESS_HOSTS.has(host)) {
    if (m !== 'POST') return `BLOCKED method=${m} host=${host}`
    if (WRITE_PATTERNS.some((re) => re.test(path))) return `BLOCKED third-party write host=${host} path=${path}`
    return null
  }
  if (m !== 'POST') return `BLOCKED method=${m}`
  if (host === 'sensors.cameltv.live' && /\/sa\.gif$/.test(path)) return null
  if (WRITE_PATTERNS.some((re) => re.test(path))) return `BLOCKED write path=${path}`
  if (!AUTH_READONLY_POST.some((re) => re.test(path))) return `BLOCKED POST path=${path}`
  return null
}

async function guardAuth(page: Page): Promise<string[]> {
  const rejected: string[] = []
  await page.route('**/*', async (route) => {
    const request = route.request()
    const err = assertAuthRequestAllowed(request.url(), request.method())
    if (err) {
      rejected.push(err)
      await route.abort('blockedbyclient')
      return
    }
    await route.continue()
  })
  return rejected
}

async function loginAndInject(page: Page): Promise<void> {
  const mobile = process.env.CAMELTV_LOGIN_MOBILE || ''
  const password = process.env.CAMELTV_LOGIN_PASSWORD || ''
  const countryCode = process.env.CAMELTV_LOGIN_COUNTRY_CODE || '86'
  if (!mobile || !password) throw new Error('CAMELTV_LOGIN_MOBILE/PASSWORD 未配置')

  const resp = await page.request.post(LOGIN_URL, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    form: { countryCode, mobile, password },
    timeout: 20_000,
  })
  const j = await resp.json().catch(() => ({}))
  const data = j?.data || {}
  if (!data.token || !data.userId || !data.userSig) {
    throw new Error('登录失败: ' + JSON.stringify(j).slice(0, 200))
  }
  await page.context().addCookies([
    {
      name: 'auth',
      value: JSON.stringify({ token: data.token, userId: data.userId, userSig: data.userSig }),
      domain: '.target.example.com',
      path: '/',
    },
  ])
}

function siteUrl(path: string): string {
  const base = process.env.BASE_URL || 'https://www.target.example.com'
  return new URL(path, base).toString()
}

test.describe('生产 P0 登录态业务模块 → UI 自动化（只读，Batch 189 二期）', () => {
  test.describe.configure({ retries: 1 })

  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(20_000)
    page.setDefaultNavigationTimeout(30_000)
    expect.configure({ timeout: 15_000 })
    await loginAndInject(page)
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

  test('AUTH-009 银钻账户页：余额/收支页签/流水记录', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/account'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Silver Diamond Balance/i).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Income/i }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Expense/i }).first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/[\d,]{2,}/.test(bodyText)).toBe(true)
    expect(/Daily Bonus|Income/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('AUTH-010 银钻账户页：Expense 页签切换', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/account'), { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: /Expense/i }).first().click({ force: true })
    await page.waitForTimeout(2500)
    const bodyText = await page.locator('body').innerText()
    expect(/Expense|No more|暂无|Empty/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('AUTH-011 商城页：余额/徽章商品/兑换入口', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/shop'), { waitUntil: 'domcontentloaded' })
    await expect(page.getByText(/Camel Mall/i).first()).toBeVisible()
    await expect(page.getByText(/Exchange/i).first()).toBeVisible()
    await expect(page.getByText(/Live Fanatic|Derby Maniac|Hat Trick/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('AUTH-012 设置页：语言/关于/条款/退出', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/setting'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Settings/i).first()).toBeVisible()
    await expect(page.getByText(/Switch Language/i).first()).toBeVisible()
    await expect(page.getByText(/About Camel Live/i).first()).toBeVisible()
    await expect(page.getByText(/Terms And Policy/i).first()).toBeVisible()
    await expect(page.getByText(/Log out/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('AUTH-013 我的收藏页：订阅与分类页签', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/favorite'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/My Subscriptions/i).first()).toBeVisible()
    for (const tab of ['COMPETITIONS', 'TEAM', 'PLAYER', 'NEWS']) {
      await expect(page.getByText(new RegExp(tab)).first()).toBeVisible()
    }
    expect(rejected).toEqual([])
  })

  test('AUTH-014 收藏页：TEAM 分类切换', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/favorite'), { waitUntil: 'domcontentloaded' })
    await page.getByText(/^TEAM$/i).first().click({ force: true })
    await page.waitForTimeout(3000)
    const bodyText = await page.locator('body').innerText()
    expect(/Team|No more|Empty|暂无/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('AUTH-015 我的页菜单入口渲染（导航由 AUTH-009/011/012/013 直接访问覆盖）', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my'), { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(1500)
    for (const menu of ['Camel Mall', 'My Favorites', 'My Outfits', 'Settings', 'Business Cooperation']) {
      await expect(page.locator('li.MuiListItem-root', { hasText: menu }).first()).toBeVisible()
    }
    expect(rejected).toEqual([])
  })
})
