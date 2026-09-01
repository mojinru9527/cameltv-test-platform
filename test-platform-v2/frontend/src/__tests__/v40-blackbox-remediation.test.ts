import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  readEnvelopeCode,
} from '@/api/requirement'
import {
  ALL_COMMAND_ROUTES,
  filterCommandRoutes,
  matchesQuery,
} from '@/components/CommandPalette'

/**
 * V4.0 生产黑盒复盘回归（P0-1 / P1-3 / P2-10）。
 * 每条断言对应一个生产实测缺陷，防止同类问题再次上线。
 */

// ── P1-3：功能拆分 404 降级 ──

describe('readEnvelopeCode（P1-3 功能拆分按钮失效根因）', () => {
  it('axios 错误自带的字符串 code 不得被当作业务码', () => {
    // 生产缺陷：`error.code` 恒为 'ERR_BAD_REQUEST'，旧实现用 ?? 短路，
    // 永远读不到 envelope 的 404，降级到「发起拆分」的分支从未生效。
    const axiosError = {
      code: 'ERR_BAD_REQUEST',
      message: '功能拆分结果',
      response: { status: 404, data: { code: 404, msg: '功能拆分结果', data: null } },
    }
    expect(readEnvelopeCode(axiosError)).toBe(404)
  })

  it('HTTP 200 + envelope code=404（拦截器 businessError）也能识别', () => {
    const businessError = Object.assign(new Error('功能拆分结果'), { code: 404 })
    expect(readEnvelopeCode(businessError)).toBe(404)
  })

  it('后端未带 envelope 时回落到 HTTP status', () => {
    const bare = { code: 'ERR_BAD_RESPONSE', response: { status: 404, data: '' } }
    expect(readEnvelopeCode(bare)).toBe(404)
  })

  it('非 404 错误不得被误判为「无结果」', () => {
    const serverError = {
      code: 'ERR_BAD_RESPONSE',
      response: { status: 500, data: { code: 500, msg: '服务器错误' } },
    }
    expect(readEnvelopeCode(serverError)).toBe(500)
  })

  it('非对象输入安全返回 undefined', () => {
    expect(readEnvelopeCode(null)).toBeUndefined()
    expect(readEnvelopeCode('boom')).toBeUndefined()
    expect(readEnvelopeCode(undefined)).toBeUndefined()
  })
})

// ── P2-10：命令面板收录 V4.0 ──

describe('命令面板（P2-10 搜不到 V4.0 功能）', () => {
  const allow = () => true

  it('AITDE 开启时可搜到智能测试任务', () => {
    const routes = filterCommandRoutes(ALL_COMMAND_ROUTES, allow, undefined, true)
    const hits = routes.filter((r) => matchesQuery(r, 'mission'))
    expect(hits.map((r) => r.path)).toContain('/missions')
  })

  it.each(['Mission', 'AI', '场景', '契约', 'aitde'])(
    '关键词「%s」不再返回空结果',
    (kw) => {
      const routes = filterCommandRoutes(ALL_COMMAND_ROUTES, allow, undefined, true)
      expect(routes.filter((r) => matchesQuery(r, kw)).length).toBeGreaterThan(0)
    },
  )

  it('AITDE 关闭时不列出主链入口（避免搜到就跳进未开放页）', () => {
    const routes = filterCommandRoutes(ALL_COMMAND_ROUTES, allow, undefined, false)
    expect(routes.some((r) => r.path === '/missions')).toBe(false)
    expect(routes.some((r) => r.path === '/healing')).toBe(false)
    // 非 AITDE 页面不受影响
    expect(routes.some((r) => r.path === '/workbench')).toBe(true)
  })

  it('AI 配置与 DSH 任务已收录（此前搜「AI」为 0 结果）', () => {
    const routes = filterCommandRoutes(ALL_COMMAND_ROUTES, allow, undefined, true)
    const paths = routes.map((r) => r.path)
    expect(paths).toContain('/ai-config')
    expect(paths).toContain('/dsh-tasks')
  })

  it('空查询返回全部可见项', () => {
    const routes = filterCommandRoutes(ALL_COMMAND_ROUTES, allow, undefined, true)
    expect(routes.every((r) => matchesQuery(r, ''))).toBe(true)
  })
})

// ── P0-1：AITDE 开关运行时跟随后端 ──

describe('AITDE 开关（P0-1 前端恒关闭）', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('后端 aitde_v3_enabled=true 时解析为 enabled（无需重建前端）', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'ok', aitde_v3_enabled: true }),
      }),
    )
    const mod = await import('@/config/aitde')
    mod.__resetAitdeV3CacheForTests('loading')
    await expect(mod.resolveAitdeV3()).resolves.toBe('enabled')
  })

  it('后端 aitde_v3_enabled=false 时解析为 disabled', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'ok', aitde_v3_enabled: false }),
      }),
    )
    const mod = await import('@/config/aitde')
    mod.__resetAitdeV3CacheForTests('loading')
    await expect(mod.resolveAitdeV3()).resolves.toBe('disabled')
  })

  it('后端不可达时是 unknown，不静默当作未开放', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
    const mod = await import('@/config/aitde')
    mod.__resetAitdeV3CacheForTests('loading')
    await expect(mod.resolveAitdeV3()).resolves.toBe('unknown')
  })

  it('探测结果被缓存，重复调用只请求一次 health', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok', aitde_v3_enabled: true }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const mod = await import('@/config/aitde')
    mod.__resetAitdeV3CacheForTests('loading')
    await Promise.all([mod.resolveAitdeV3(), mod.resolveAitdeV3(), mod.resolveAitdeV3()])
    await mod.resolveAitdeV3()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith('/api/v2/health', expect.anything())
  })
})
