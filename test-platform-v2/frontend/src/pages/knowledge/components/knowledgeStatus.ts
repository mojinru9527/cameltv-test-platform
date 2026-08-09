const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: '待审核',
  approved: '已采纳',
  rejected: '已驳回',
  imported: '已导入',
  draft: '草稿',
}

const SOURCE_STATUS_LABELS: Record<string, string> = {
  active: '生效中',
  parsed: '已解析',
  pending: '待处理',
  deprecated: '已废弃',
  superseded: '已替代',
  syncing: '同步中',
  failed: '失败',
}

function unknownStatus(status: string): string {
  return status ? `未知状态（${status}）` : '未知状态'
}

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABELS[status] ?? unknownStatus(status)
}

export function sourceStatusLabel(status: string): string {
  return SOURCE_STATUS_LABELS[status] ?? unknownStatus(status)
}
