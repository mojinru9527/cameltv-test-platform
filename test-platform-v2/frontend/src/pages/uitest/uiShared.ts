import { execStatusLabel, normalizeExecStatus } from '@/utils/executionStatus'
import type { Environment, UiJobItem } from '@/types'

export const BROWSER_MAP: Record<string, { color: string }> = {
  chromium: { color: 'blue' },
  firefox: { color: 'orange' },
  webkit: { color: 'purple' },
}

function browserColorBadgeClass(c: string) {
  const map: Record<string, string> = {
    blue: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
    orange: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
    purple: 'border-status-accent-border bg-status-accent-muted text-status-accent dark:border-status-accent-border dark:bg-status-accent-muted dark:text-status-accent',
  }
  return map[c] ?? ''
}

export function browserBadgeClass(c: string) {
  return browserColorBadgeClass(c)
}

/** 执行状态徽标类名：按规范值取色，兼容历史旧值（done/fail/success 等）。 */
const STATUS_CLASS: Record<string, string> = {
  pending: 'border-border bg-muted text-muted-foreground',
  running: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
  passed: 'border-status-success-border bg-status-success-muted text-status-success dark:border-status-success-border dark:bg-status-success-muted dark:text-status-success',
  failed: 'border-status-danger-border bg-status-danger-muted text-status-danger dark:border-status-danger-border dark:bg-status-danger-muted dark:text-status-danger',
  cancelled: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
  skipped: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
  blocked: 'border-status-danger-border bg-status-danger-muted text-status-danger dark:border-status-danger-border dark:bg-status-danger-muted dark:text-status-danger',
}

export function statusBadgeClass(status?: string): string {
  return STATUS_CLASS[normalizeExecStatus(status)] ?? 'border-border bg-muted text-muted-foreground'
}

/** 任务状态筛选选项：保持既有筛选值不变，标签使用统一词表。 */
export const JOB_STATUS_FILTERS = [
  { value: 'idle', label: execStatusLabel('idle') },
  { value: 'running', label: execStatusLabel('running') },
  { value: 'done', label: execStatusLabel('done') },
  { value: 'fail', label: execStatusLabel('fail') },
]

export function getEnvironment(environments: Environment[], job: UiJobItem) {
  return environments.find((environment) => environment.id === job.environment_id) ?? null
}

export function isProductionJob(environments: Environment[], job: UiJobItem) {
  const environment = getEnvironment(environments, job)
  return environment?.is_production === true || environment?.env_type === 'prod'
}
