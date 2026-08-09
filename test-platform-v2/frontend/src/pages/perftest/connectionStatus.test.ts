import { describe, expect, it } from 'vitest'

import { perfConnectionLabel } from './connectionStatus'

describe('performance connection status', () => {
  it('does not claim to be connecting before monitoring starts', () => {
    expect(perfConnectionLabel(false, 'disconnected')).toBe('等待采集')
  })

  it('describes active websocket and polling modes', () => {
    expect(perfConnectionLabel(true, 'websocket')).toBe('WebSocket 实时')
    expect(perfConnectionLabel(true, 'polling')).toBe('HTTP 轮询(降级)')
    expect(perfConnectionLabel(true, 'disconnected')).toBe('连接中…')
  })
})
