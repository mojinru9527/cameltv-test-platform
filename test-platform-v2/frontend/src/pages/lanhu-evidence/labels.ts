/**
 * 蓝湖证据包状态中文映射（Batch 92）。
 * 纯函数，便于单测；Badge tone 用 @/ui 语义色（success/warning/danger/info/neutral）。
 */
import type { BadgeTone } from '@/ui'

const JOB_STATUS_LABEL: Record<string, string> = {
  pending: '排队中',
  running: '采集中',
  success: '成功',
  success_with_warnings: '成功(有告警)',
  failed: '失败',
  cancelled: '已取消',
}

const JOB_STATUS_TONE: Record<string, BadgeTone> = {
  pending: 'neutral',
  running: 'info',
  success: 'success',
  success_with_warnings: 'warning',
  failed: 'danger',
  cancelled: 'neutral',
}

const STAGE_LABEL: Record<string, string> = {
  queued: '排队中',
  discovering: '发现页面',
  capturing: '截图中',
  exporting: '导出中',
  done: '已完成',
}

const PAGE_CAPTURE_LABEL: Record<string, string> = {
  success: '已捕获',
  failed: '失败',
  skipped: '跳过',
}

const PAGE_OCR_LABEL: Record<string, string> = {
  success: '已识别',
  unavailable: '无文本(待审核)',
  pending: '待处理',
}

const REVIEW_STATUS_LABEL: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
}

export function jobStatusLabel(status: string): string {
  return JOB_STATUS_LABEL[status] ?? status
}

export function jobStatusTone(status: string): BadgeTone {
  return JOB_STATUS_TONE[status] ?? 'neutral'
}

export function stageLabel(stage: string): string {
  return STAGE_LABEL[stage] ?? stage
}

export function pageCaptureLabel(status: string): string {
  return PAGE_CAPTURE_LABEL[status] ?? status
}

export function pageOcrLabel(status: string): string {
  return PAGE_OCR_LABEL[status] ?? status
}

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABEL[status] ?? status
}
