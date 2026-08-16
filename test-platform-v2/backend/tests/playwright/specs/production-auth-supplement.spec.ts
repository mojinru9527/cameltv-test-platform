import { expect, test, type Page } from '@playwright/test'

/**
 * 生产 P0 登录态补充 UI 自动化（只读，Batch 189）。
 *
 * 登录机制：beforeEach 用测试账号调用 demo/login（form 编码）获取
 * token/userId/userSig，注入站点 auth Cookie（token 字段=32hex token），
 * 之后所有页面以登录态渲染。凭据经 CAMELTV_LOGIN_* 环境变量注入
 * （平台 Runner 透传 CAMELTV_ 前缀，见 PR #260）。
 *
 * 守卫：GET/HEAD 全放行；业务主机 POST 仅放行查询白名单（登录/余额/配置/
 * 列表/搜索/预测查询）；一切写型 POST（预测提交/支付/提现等）拦截并断言为 0。
 */

const SITE_HOSTS = new Set(['www.camel1.tv', 'camel1.tv', 'www.cameltv.live', 'cameltv.live', 'www.camel1.to', 'camel1.to'])
const LOGIN_URL = 'https://api.cameltv.live/account-service/ee/client/demo/login'
const MATCH_URL = '/football/tottenham-hotspur-vs-tsg-hoffenheim/l7oqdehgv6nnr51'

// 业务主机查询型 POST 白名单（登录态渲染所需，全部为只读查询）
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
  /\/ee\/diamond\/account$/,
  /\/ee\/silverDiamond\/(account|task|event|invite\/home|invite\/recordList)$/,
  /\/ee\/client\/demo\/login$/,
  /\/ee\/faq\/(list|one|get_full)$/,
  /\/ee\/replay\/list$/,
  /\/ee\/block_speak\/list$/,
  /\/ee\/article\/home$/,
  /\/ee\/invite\/home$/,
]

const WRITE_PATTERNS: RegExp[] = [
  /bet|cancel|pay|order|refund|recharge|withdraw|deposit|favorite|like\b|comment|review|create|save|update|delete|add|remove|send|publish|bonus|gift|diamond\/withdraw|invite\/bind|feedback|report/,
]

const BUSINESS_HOSTS = new Set(['api.cameltv.live', 'www.camel1.tv', 'www.cameltv.live', 'livecdn.cameltv.live', 'img.cameltv.live', 'sensors.cameltv.live'])

function assertAuthRequestAllowed(rawUrl: string, method: string): string | null {
  const url = new URL(rawUrl)
  const m = method.trim().toUpperCase()
  if (m === 'GET' || m === 'HEAD') return null
  const path = url.pathname
  const host = url.hostname.toLowerCase()
  // 非业务主机（第三方遥测/分析/广告）：POST 仅拦截写型路径，遥测信标放行
  if (!BUSINESS_HOSTS.has(host)) {
    if (m !== 'POST') return `BLOCKED method=${m} host=${host}`
    if (WRITE_PATTERNS.some((re) => re.test(path))) return `BLOCKED third-party write host=${host} path=${path}`
    return null
  }
  if (m !== 'POST') return `BLOCKED method=${m}`
  // sensors 打点（sa.gif）放行
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
      domain: '.camel1.tv',
      path: '/',
    },
  ])
}

async function stayOnSite(page: Page): Promise<void> {
  const host = new URL(page.url()).hostname.toLowerCase()
  expect(SITE_HOSTS.has(host), `页面被劫持到非站点主机: ${host}`).toBe(true)
}

function siteUrl(path: string): string {
  const base = process.env.BASE_URL || 'https://www.camel1.tv'
  return new URL(path, base).toString()
}

test.describe('体育平台 生产 P0 登录态补充用例 → UI 自动化（只读，Batch 189）', () => {
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

  test('AUTH-001 我的页登录态：用户ID/银钻余额/菜单齐全', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/11025728/i).first()).toBeVisible()
    await expect(page.getByText(/Silver Diamond/i).first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/[\d,]{2,}/.test(bodyText)).toBe(true)
    for (const menu of ['Free Silver Diamond', 'Camel Mall', 'My Favorites', 'My Outfits', 'FAQ & Feedback', 'Settings', 'User Feedback']) {
      await expect(page.getByText(new RegExp(menu)).first()).toBeVisible()
    }
    expect(rejected).toEqual([])
  })

  test('AUTH-002 预测记录页：Current/All 页签与空态', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/prediction/history'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Prediction Record/i).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Current/i }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /^All$/i }).first()).toBeVisible()
    await page.getByRole('button', { name: /^All$/i }).first().click({ force: true })
    await page.waitForTimeout(2000)
    const bodyText = await page.locator('body').innerText()
    expect(/No more data|Prediction/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('AUTH-003 邀请好友页：进度/记录/步骤渲染', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/invite'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Invite Friends Campaign/i).first()).toBeVisible()
    await expect(page.getByText(/Invitation Progress/i).first()).toBeVisible()
    await expect(page.getByText(/Invitation Records/i).first()).toBeVisible()
    await expect(page.getByText(/Invitation Steps/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('AUTH-004 首页登录态：赛事渲染正常且不跳离站点', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/'), { waitUntil: 'networkidle' })
    await stayOnSite(page)
    await expect(page.getByText(/Live Matches|Favorites|Competitions/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('AUTH-005 搜索登录态：分类结果正常', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/search#q=Real%20Madrid&f=home'), { waitUntil: 'networkidle' })
    for (const tab of ['ALL', 'MATCH', 'TEAM', 'PLAYER', 'NEWS']) {
      await expect(page.getByText(new RegExp(`^${tab}$`)).first()).toBeVisible()
    }
    await expect(page.locator('a[href*="/team/"]').first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('AUTH-006 赛事详情登录态：预测区/直播间渲染', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl(MATCH_URL), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Prediction/i).first()).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(/1X2|Home Win|Draw|Away Win|Odds/i.test(bodyText)).toBe(true)
    expect(rejected).toEqual([])
  })

  test('AUTH-007 反馈表单登录态：字段与计数', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/feedback'), { waitUntil: 'networkidle' })
    await expect(page.getByText(/Issue Type/i).first()).toBeVisible()
    await expect(page.getByText(/0\/500/i).first()).toBeVisible()
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible()
    await textarea.fill('x'.repeat(20))
    await expect(page.getByText(/20\/500/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('AUTH-008 FAQ 登录态：问题列表与详情链接', async ({ page }) => {
    const rejected = await guardAuth(page)
    await page.goto(siteUrl('/my/faq'), { waitUntil: 'networkidle' })
    await expect(page.locator('a[href*="/my/faq/"]').first()).toBeVisible()
    await expect(page.getByText(/Load More/i).first()).toBeVisible()
    expect(rejected).toEqual([])
  })
})
