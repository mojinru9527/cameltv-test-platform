import { aitdeV2 } from './missions'

export interface ScopeItem {
  id: number
  mission_id: number
  scope_key: string
  scope_type: string
  name: string
  decision: 'INCLUDE' | 'EXCLUDE' | string
  test_depth: string
  risk_level: string
  reason: string
  ai_confidence: number
  review_status: 'PROPOSED' | 'APPROVED' | 'REJECTED' | string
  created_by_type: string
  created_at: string | null
  updated_at: string | null
}

export interface ScopeSummary {
  total: number
  approved: number
  rejected: number
  proposed: number
  review_progress: number
  include_count: number
  exclude_count: number
}

export interface ScopeReviewItemInput {
  scope_key: string
  decision: 'INCLUDE' | 'EXCLUDE'
  action: 'approve' | 'reject'
  reason?: string | null
}

export function analyzeMissionScope(
  missionId: number,
  payload: { force?: boolean; model?: string } = {},
): Promise<{ operation_id: string | null; status: string; items: number }> {
  return aitdeV2.post(`/missions/${missionId}/scope/analyze`, payload)
}

export function fetchMissionScope(
  missionId: number,
  signal?: AbortSignal,
): Promise<{ items: ScopeItem[]; summary: ScopeSummary }> {
  return aitdeV2.get(`/missions/${missionId}/scope`, { signal })
}

export function reviewMissionScope(
  missionId: number,
  items: ScopeReviewItemInput[],
): Promise<ScopeSummary> {
  return aitdeV2.post(`/missions/${missionId}/scope/reviews`, { items })
}

export const SCOPE_TYPE_LABELS: Record<string, string> = {
  FEATURE: '功能',
  BUSINESS_FLOW: '业务流程',
  PAGE: '页面',
  API: '接口',
  DATA_STATE: '数据状态',
  RISK: '风险',
  REGRESSION_AREA: '回归域',
}

export const DECISION_LABELS: Record<string, { label: string; color: string }> = {
  INCLUDE: { label: '纳入', color: 'bg-status-success-muted text-status-success' },
  EXCLUDE: { label: '排除', color: 'bg-muted text-muted-foreground' },
}

export const REVIEW_LABELS: Record<string, { label: string; color: string }> = {
  PROPOSED: { label: '待评审', color: 'bg-status-warning-muted text-status-warning' },
  APPROVED: { label: '已批准', color: 'bg-status-success-muted text-status-success' },
  REJECTED: { label: '已拒绝', color: 'bg-status-danger-muted text-status-danger' },
}

export const RISK_LABELS: Record<string, string> = {
  P0: 'P0',
  P1: 'P1',
  P2: 'P2',
  P3: 'P3',
}
