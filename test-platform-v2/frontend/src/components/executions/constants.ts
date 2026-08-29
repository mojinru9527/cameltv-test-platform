/** Shared execution UI label/colour maps used across the execution components. */

export const ASSERTION_RESULT_LABELS: Record<string, { label: string; color: string }> = {
  PASS: { label: '通过', color: 'bg-status-success-muted text-status-success' },
  FAIL: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
  BLOCKED: { label: '阻塞', color: 'bg-muted text-muted-foreground' },
  INCONCLUSIVE: { label: '无法判定', color: 'bg-status-warning-muted text-status-warning' },
}

export const STEP_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  SUCCESS: { label: '成功', color: 'bg-status-success-muted text-status-success' },
  FAILED: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
  RUNNING: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  PENDING: { label: '等待', color: 'bg-muted text-muted-foreground' },
  SKIPPED: { label: '跳过', color: 'bg-muted text-muted-foreground' },
}
