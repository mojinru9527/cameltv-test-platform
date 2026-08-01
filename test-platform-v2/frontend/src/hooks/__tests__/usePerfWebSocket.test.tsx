import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'
import { resolvePerfWebSocketUrl, usePerfWebSocket } from '../usePerfWebSocket'

vi.mock('@/api/perftest', () => ({
  fetchMetrics: vi.fn().mockResolvedValue({ metrics: [] }),
}))

class WebSocketStub {
  static urls: string[] = []

  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null

  constructor(url: string | URL) {
    WebSocketStub.urls.push(String(url))
  }

  close() {}
}

describe('usePerfWebSocket', () => {
  afterEach(() => {
    WebSocketStub.urls = []
    vi.unstubAllGlobals()
  })

  it('uses the selected project and never puts the JWT in the socket URL', async () => {
    useAuthStore.setState({
      token: 'must-not-appear-in-url',
      currentProjectId: 7,
    })
    vi.stubGlobal('WebSocket', WebSocketStub)

    const view = renderHook(() => usePerfWebSocket({
      sessionId: 42,
      enabled: true,
    }))

    await waitFor(() => expect(WebSocketStub.urls).toHaveLength(1))
    expect(WebSocketStub.urls[0]).toContain('/api/v1/perf-sessions/42/stream?project_id=7')
    expect(WebSocketStub.urls[0]).not.toContain('must-not-appear-in-url')

    view.unmount()
  })

  it('resolves the socket against the current origin for proxy deployment', () => {
    expect(resolvePerfWebSocketUrl(42, 7, '/api/v1', 'https://qa.example.com'))
      .toBe('wss://qa.example.com/api/v1/perf-sessions/42/stream?project_id=7')
  })

  it('uses the API origin and path for a physically separated deployment', () => {
    expect(resolvePerfWebSocketUrl(
      42,
      7,
      'http://127.0.0.1:8026/gateway/api/v1/',
      'https://frontend.example.com',
    )).toBe('ws://127.0.0.1:8026/gateway/api/v1/perf-sessions/42/stream?project_id=7')
  })
})
