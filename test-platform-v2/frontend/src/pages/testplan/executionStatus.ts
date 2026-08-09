const EXECUTION_STATUS_LABELS: Record<string, string> = {
  pass: '通过',
  fail: '失败',
  skip: '跳过',
  block: '阻塞',
  pending: '待执行',
}

export function executionStatusLabel(status: unknown): string {
  if (typeof status !== 'string' || !status) return '-'
  return EXECUTION_STATUS_LABELS[status] || `未知状态（${status}）`
}
