import { describe, expect, it, vi, beforeEach } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'

/**
 * B60-P0-003 契约：请求拦截器必须在“发出请求那一刻”读取当前项目，
 * 保证项目 A→B 切换后任何写/读请求都携带 B 的 X-Project-Id。
 */
describe('client 项目头注入', () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: 'test-token',
      currentProjectId: 1,
      user: { id: 1, username: 'admin', roles: ['admin'] },
    })
  })

  it('请求时读取当前项目并注入 X-Project-Id', async () => {
    const adapter = vi.fn(async (config) => ({
      data: { code: 0, msg: 'ok', data: [] },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }))

    useAuthStore.setState({ currentProjectId: 5 })
    await client.get('/testcase', { adapter: adapter as never })

    const sentConfig = adapter.mock.calls[0][0] as { headers: Record<string, string> }
    expect(sentConfig.headers['X-Project-Id']).toBe('5')
  })

  it('无项目时不注入 X-Project-Id', async () => {
    const adapter = vi.fn(async (config) => ({
      data: { code: 0, msg: 'ok', data: [] },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }))

    useAuthStore.setState({ currentProjectId: null })
    await client.get('/report', { adapter: adapter as never })

    const sentConfig = adapter.mock.calls[0][0] as { headers: Record<string, string> }
    expect(sentConfig.headers['X-Project-Id']).toBeUndefined()
  })
})
