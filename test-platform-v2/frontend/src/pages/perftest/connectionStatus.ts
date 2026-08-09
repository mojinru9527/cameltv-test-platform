export type PerfConnectionMode = 'websocket' | 'polling' | 'disconnected'

export function perfConnectionLabel(monitoring: boolean, mode: PerfConnectionMode): string {
  if (!monitoring) return '等待采集'
  if (mode === 'websocket') return 'WebSocket 实时'
  if (mode === 'polling') return 'HTTP 轮询(降级)'
  return '连接中…'
}
