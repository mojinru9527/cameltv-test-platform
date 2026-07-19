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
  acknowledged: { color: 'orange', label: '已确认' },
  fixing: { color: 'processing', label: '修复中' },
  reviewing: { color: 'purple', label: '待审核' },
  verified: { color: 'green', label: '已验证' },
  closed: { color: 'default', label: '已关闭' },
  reopened: { color: 'red', label: '已重开' },
  // legacy compatibility (backend normalizes these)
  confirmed: { color: 'orange', label: '已确认' },
  pending_review: { color: 'purple', label: '待回归' },
  rejected: { color: 'default', label: '已拒绝' },
  in_progress: { color: 'processing', label: '处理中' },
  resolved: { color: 'green', label: '已解决' },
  wontfix: { color: 'default', label: '不修复' },
}

export const STATUS_TRANSITIONS: Record<string, string[]> = {
  'open': ['acknowledged', 'closed'],
  'acknowledged': ['fixing', 'closed'],
  'fixing': ['reviewing', 'closed'],
  'reviewing': ['verified', 'reopened'],
  'verified': ['closed', 'reopened'],
  'closed': ['reopened'],
  'reopened': ['acknowledged', 'closed'],
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function severityBadgeClass(c: string) {
  const map: Record<string, string> = {
    red: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400',
    orange: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-400',
    gold: 'border-yellow-200 bg-yellow-50 text-yellow-700 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-400',
    blue: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
  }
  return map[c] ?? ''
}

export function statusBadgeClass(c: string) {
  const map: Record<string, string> = {
    red: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400',
    processing: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
    green: 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400',
    default: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-400',
  }
  return map[c] ?? ''
}
