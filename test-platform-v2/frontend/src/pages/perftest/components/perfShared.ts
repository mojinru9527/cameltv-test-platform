export const METRIC_LABELS: Record<string, string> = {
  cpu: 'CPU', memory: '内存', fps: '帧率', jank: '卡顿(Jank)',
  startup: '启动耗时', anr: 'ANR/崩溃',
}
export const METRIC_UNITS: Record<string, string> = {
  cpu: '%', memory: 'MB', fps: 'fps', jank: '次', startup: 'ms', anr: '次',
}
export const STATUS_LABELS: Record<string, string> = {
  pending: '等待中', running: '采集中', completed: '已完成', failed: '失败', cancelled: '已取消',
}
export const STATUS_TONES: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  pending: 'neutral', running: 'info', completed: 'success', failed: 'danger', cancelled: 'neutral',
}

export function isCollectorUnavailable(error: unknown): boolean {
  if (!error || typeof error !== 'object' || !('response' in error)) return false
  const response = (error as { response?: { status?: number } }).response
  return response?.status === 503
}
