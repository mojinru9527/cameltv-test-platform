/**
 * Batch 110 — 生产 P0 UI 自动化只读守卫与运行时（体育平台）。
 *
 * 在 batch-101 冒烟守卫基础上细化：除 GET/HEAD 外，放行「查询型 POST」
 * （搜索/资讯列表/广告查询/匿名登录/konfi 配置读取/直播间查询等），
 * 仍拦截一切写型端点（支付/下单/收藏/点赞/评论/提现/充值等）。
 */

export interface P0Runtime {
  baseUrl: URL
  allowedHosts: ReadonlySet<string>
  expectedBusinessText: string
  owner: string
}

export function readP0Runtime(environment: Record<string, string | undefined> = process.env): P0Runtime {
  const owner = environment.PROD_SMOKE_OWNER?.trim() || 'UNASSIGNED'
  const rawBaseUrl = environment.BASE_URL?.trim()
  if (!rawBaseUrl) throw new Error('BASE_URL is required')
  const baseUrl = new URL(rawBaseUrl)
  if (baseUrl.protocol !== 'https:') throw new Error('BASE_URL must be HTTPS')
  const allowedHosts = new Set(
    (environment.PROD_ALLOWED_HOSTS || '')
      .split(',')
      .map((h) => h.trim().toLowerCase())
      .filter(Boolean),
  )
  if (!allowedHosts.has(baseUrl.hostname.toLowerCase())) {
    throw new Error('BASE_URL host is not allowlisted in PROD_ALLOWED_HOSTS')
  }
  return {
    baseUrl,
    allowedHosts,
    expectedBusinessText: environment.PROD_EXPECTED_BUSINESS_TEXT?.trim() || '',
    owner,
  }
}

// 查询型 POST 白名单（路径片段匹配，全部为生产实测只读查询）
const READONLY_POST_PATTERNS: RegExp[] = [
  /\/ee\/ads\/activity\/get$/,
  /\/ee\/search\/(hot|query|recommend)$/,
  /\/ee\/news\/(list_visible|related|get_visible|get)$/,
  /\/ee\/client\/(getHistoryMessage|web\/getAnchorNoticeMapper)$/,
  /\/login\/anonymous\/web$/,
  /\/konfi-service\/web\/getDataById$/,
  /\/ee\/sports_live\/(view_match|loadAnchorsByMatchId|heartbeat)$/,
  /\/ee\/sports_live\/football\/match\/analysis$/,
  // Batch 187：预测模块查询型 POST（预测列表/预测记录/预测首页/赔率查询，只读）
  /\/ee\/forecast\/(match_list|user_list|index|queryOddsSummaryByMatchId|realtime\/odds)$/,
]

// 写型路径特征（禁止命中，命中即拦截）
const WRITE_PATTERNS: RegExp[] = [
  /pay|order|refund|recharge|withdraw|deposit|favorite|like\b|comment|review|create|save|update|delete|add|remove|send|publish|bonus|gift|diamond/,
]

// 业务 API 主机：严格守卫（GET/HEAD + 查询型 POST 白名单）
const BUSINESS_HOSTS = new Set([
  'api.cameltv.live',
  'www.camel1.tv',
  'www.cameltv.live',
  'livecdn.cameltv.live',
  'img.cameltv.live',
  'sensors.cameltv.live',
])

// 第三方遥测/分析 POST（g/collect、sa.gif 等）：只读统计，放行
const TELEMETRY_POST_PATTERNS: RegExp[] = [/\/g\/collect$/, /\/collect$/, /\/sa\.gif$/, /\/log$/, /\/beacon$/, /\/pageview/]

export function assertP0RequestAllowed(
  runtime: P0Runtime,
  rawUrl: string,
  method: string,
): void {
  const url = new URL(rawUrl)
  const normalizedMethod = method.trim().toUpperCase()
  // 只读 GET/HEAD 对任意主机放行（含第三方广告/分析/字体 CDN，数据中心 IP 下必现且域名轮换）。
  if (normalizedMethod === 'GET' || normalizedMethod === 'HEAD') return
  const path = url.pathname
  const host = url.hostname.toLowerCase()
  // C101-1 只读策略（Batch 110 登记）：业务主机外（第三方分析/广告/登录域）的 POST 视为
  // 只读遥测/信标放行，但写型路径（支付/下单/收藏/评论等）一律拦截。
  // 用「非写型即放行」而非路径清单，避免数据中心 IP 下遥测域名轮换导致逐域打补丁
  // （Batch 112 实测 analytics/doubleclick/csp.withgoogle 等）。
  if (!BUSINESS_HOSTS.has(host)) {
    if (normalizedMethod !== 'POST') {
      throw new Error(`BLOCKED method=${normalizedMethod} not allowed in P0 read-only`)
    }
    if (WRITE_PATTERNS.some((re) => re.test(path))) {
      throw new Error(`BLOCKED third-party write-like POST host=${host} path=${path}`)
    }
    return
  }
  // 业务主机内仍严格按主机白名单 + 查询型 POST 白名单拦截。
  if (!runtime.allowedHosts.has(url.hostname.toLowerCase())) {
    throw new Error(`BLOCKED host=${url.hostname} not allowlisted`)
  }
  if (normalizedMethod !== 'POST') {
    throw new Error(`BLOCKED method=${normalizedMethod} not allowed in P0 read-only`)
  }
  if (url.hostname === 'sensors.cameltv.live' && /\/sa\.gif$/.test(path)) return
  if (WRITE_PATTERNS.some((re) => re.test(path))) {
    throw new Error(`BLOCKED write-like POST path=${path}`)
  }
  if (!READONLY_POST_PATTERNS.some((re) => re.test(path))) {
    throw new Error(`BLOCKED POST path=${path} not in read-only query allowlist`)
  }
}
