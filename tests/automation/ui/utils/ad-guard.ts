/**
 * 广告专项处理基线（Ad Guard）— CamelTv UI 自动化全局广告防御。
 *
 * 背景：camel1.tv 线上实测存在第三方广告联盟（popunder 新窗口跳转
 * 成人/博彩落地页）与赌博 Banner，会干扰 UI 自动化批量执行稳定性。
 * 本工具为所有测试提供统一广告防御：
 *
 *  1. 广告域请求拦截  — 在浏览器层面直接 abort 已知广告联盟域，
 *                       从源头杜绝 popunder/弹窗注入（默认开启）
 *  2. popup 自动关闭   — 兜底：拦截未命中时弹出新窗口，立即关闭并记录
 *  3. 主框架跳转恢复   — 兜底：被整页跳转到广告域时，goBack 返回主站
 *                       继续执行（对应测试需求：广告页要能返回继续探索）
 *
 * 用法：
 *  - 普通测试：无需改动，`ai-test.ts` fixture 默认安装 Ad Guard
 *  - 广告专项测试：用 `createAdObservationFixture()` 关闭拦截，
 *    真实观察弹窗行为并断言「弹出 → 关闭/返回 → 主流程继续」
 *
 * 注意：popup/跳转事件在 page 创建后立即挂载，避免广告在导航早期触发。
 */
import type { BrowserContext, Page } from '@playwright/test'

/** 线上实测的广告联盟域（2026-08 探索结论）。新域可在 .env 的 AD_BLOCK_DOMAINS 追加，逗号分隔。 */
export const DEFAULT_AD_DOMAINS: readonly string[] = [
  'andallthemise.org',
  'eflewandatnig.org',
  'ukankingwithea.com',
  'bestfungamestoday.com',
  'moonlighthathel.org',
  'take-look.com',
]

/** 从环境变量读取自定义广告域（逗号分隔，追加到默认列表）。 */
export function resolvedAdDomains(): string[] {
  const extra = process.env.AD_BLOCK_DOMAINS?.trim()
  if (!extra) return [...DEFAULT_AD_DOMAINS]
  const parsed = extra
    .split(',')
    .map((d) => d.trim().toLowerCase())
    .filter(Boolean)
  return [...new Set([...DEFAULT_AD_DOMAINS, ...parsed])]
}

export interface AdGuardOptions {
  /** 是否拦截广告域请求（默认 true）。广告专项测试传 false。 */
  blockRequests?: boolean
  /** 是否自动关闭 popup（默认 true）。 */
  closePopups?: boolean
  /** 是否在整页跳转广告域后自动返回（默认 true）。 */
  recoverMainFrame?: boolean
  /** 可选：广告事件回调（专项测试用于断言）。 */
  onAdEvent?: (event: AdEvent) => void
}

export interface AdEvent {
  type: 'request-blocked' | 'popup-opened' | 'popup-closed' | 'mainframe-recovered'
  url: string
  at: number
}

/**
 * 为单个 page 安装广告防御。
 * 返回 disposer；测试结束时调用以解除监听（避免跨测试泄漏）。
 */
export function installAdGuard(
  page: Page,
  options: AdGuardOptions = {},
): () => void {
  const {
    blockRequests = true,
    closePopups = true,
    recoverMainFrame = true,
    onAdEvent,
  } = options
  const domains = resolvedAdDomains()

  const isAdUrl = (url: string): boolean => {
    try {
      const host = new URL(url).hostname.toLowerCase()
      return domains.some((d) => host === d || host.endsWith(`.${d}`))
    } catch {
      return false
    }
  }

  // 1) 请求拦截：广告域请求直接 abort（含脚本/图片/iframe 资源）
  let routeDisposer: (() => void) | undefined
  if (blockRequests) {
    page
      .route('**/*', async (route) => {
        const url = route.request().url()
        if (isAdUrl(url)) {
          onAdEvent?.({ type: 'request-blocked', url, at: Date.now() })
          await route.abort('blockedbyclient')
          return
        }
        await route.continue()
      })
      .then((disposable) => {
        routeDisposer = () => disposable.dispose()
      })
      .catch(() => {
        /* route 注册失败不阻塞测试主流程 */
      })
  }

  // 2) popup 自动关闭
  const popupHandler = (popup: Page) => {
    const url = popup.url() || '(loading)'
    onAdEvent?.({ type: 'popup-opened', url, at: Date.now() })
    if (closePopups) {
      popup
        .close()
        .then(() => onAdEvent?.({ type: 'popup-closed', url, at: Date.now() }))
        .catch(() => {
          /* popup 可能已自行关闭 */
        })
    }
  }
  page.on('popup', popupHandler)

  // 3) 主框架跳转恢复：被整页跳转到广告域时返回主站
  const navigationHandler = (frame: { url: () => string; parentFrame: () => unknown }) => {
    if (!recoverMainFrame) return
    // 仅处理主框架导航（无父 frame 即主框架）
    if (frame.parentFrame()) return
    const url = frame.url()
    if (isAdUrl(url)) {
      onAdEvent?.({ type: 'mainframe-recovered', url, at: Date.now() })
      page.goBack({ timeout: 5000 }).catch(() => {
        /* 无历史可返回时忽略 */
      })
    }
  }
  page.on('framenavigated', navigationHandler)

  return () => {
    page.off('popup', popupHandler)
    page.off('framenavigated', navigationHandler)
    routeDisposer?.()
    routeDisposer = undefined
  }
}

/**
 * 安装到 BrowserContext 级：每个新 page 自动获得广告防御。
 * 在 fixture 的 context 上调用一次即可覆盖全部页面（含测试内新开的 tab）。
 */
export function installAdGuardOnContext(
  context: BrowserContext,
  options: AdGuardOptions = {},
): () => void {
  const disposers: Array<() => void> = []
  const onPage = (page: Page) => {
    disposers.push(installAdGuard(page, options))
  }
  context.on('page', onPage)
  // 已有页面立即安装
  for (const page of context.pages()) onPage(page)
  return () => {
    context.off('page', onPage)
    disposers.forEach((d) => d())
  }
}
