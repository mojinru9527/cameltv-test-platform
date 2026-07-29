/**
 * Defect page shared constants, maps, and helpers.
 * Extracted from index.tsx to avoid circular deps with sub-components.
 */

export const SEVERITY_MAP: Record<string, { color: string; label: string }> = {
  P0: { color: 'red', label: 'P0-致命' },
  P1: { color: 'orange', label: 'P1-严重' },
  P2: { color: 'gold', label: 'P2-一般' },
  P3: { color: 'blue', label: 'P3-建议' },
}

export const STATUS_MAP: Record<string, { color: string; label: string }> = {
  open: { color: 'red', label: '待处理' },
  confirmed: { color: 'orange', label: '已确认' },
  fixing: { color: 'processing', label: '修复中' },
  pending_review: { color: 'purple', label: '待回归' },
  closed: { color: 'default', label: '已关闭' },
  rejected: { color: 'default', label: '已拒绝' },
}

export const STATUS_TRANSITIONS: Record<string, string[]> = {
  open: ['confirmed', 'rejected'],
  confirmed: ['fixing', 'rejected'],
  fixing: ['pending_review'],
  pending_review: ['closed', 'fixing'],
  closed: [],
  rejected: ['open'],
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function severityBadgeClass(c: string) {
  const map: Record<string, string> = {
    red: 'border-status-danger-border bg-status-danger-muted text-status-danger dark:border-status-danger-border dark:bg-status-danger-muted dark:text-status-danger',
    orange: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
    gold: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
    blue: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
  }
  return map[c] ?? ''
}

export function statusBadgeClass(c: string) {
  const map: Record<string, string> = {
    red: 'border-status-danger-border bg-status-danger-muted text-status-danger dark:border-status-danger-border dark:bg-status-danger-muted dark:text-status-danger',
    processing: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
    green: 'border-status-success-border bg-status-success-muted text-status-success dark:border-status-success-border dark:bg-status-success-muted dark:text-status-success',
    default: 'border-border bg-muted text-muted-foreground',
  }
  return map[c] ?? ''
}
