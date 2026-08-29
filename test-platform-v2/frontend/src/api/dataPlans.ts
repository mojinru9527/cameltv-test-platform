import { aitdeV2 } from './missions'

// ── AITDE V3.2 Data + DB Runtime: Data Plan domain ──

export interface DataPlanStep {
  id: number
  sequence: number
  step_type: string
  driver: string
  command_json: Record<string, unknown> | null
  compensation_json: Record<string, unknown> | null
  status: string
}

export interface DataPlan {
  id: number
  scenario_version_id: number
  environment_id: number | null
  status: string
  strategy: string
  plan_hash: string
  risk_level: string
  created_by_type: string
  created_at: string | null
  approved_by: number | null
  approved_at: string | null
  steps: DataPlanStep[]
}

export interface CreateDataPlanInput {
  environment_id?: number | null
  strategy?: string
}

export function createDataPlan(
  scenarioVersionId: number,
  payload: CreateDataPlanInput = {},
): Promise<DataPlan> {
  return aitdeV2.post(`/scenarios/${scenarioVersionId}/data-plans`, payload)
}

export function fetchDataPlan(planId: number, signal?: AbortSignal): Promise<DataPlan> {
  return aitdeV2.get(`/data-plans/${planId}`, { signal })
}

export function approveDataPlan(planId: number): Promise<DataPlan> {
  return aitdeV2.post(`/data-plans/${planId}/approve`)
}

// ── UI label/colour maps ──

export const DATA_PLAN_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'bg-muted text-muted-foreground' },
  PENDING_APPROVAL: { label: '待审批', color: 'bg-status-warning-muted text-status-warning' },
  APPROVED: { label: '已批准', color: 'bg-status-success-muted text-status-success' },
  REJECTED: { label: '已拒绝', color: 'bg-status-danger-muted text-status-danger' },
  EXECUTING: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  COMPLETED: { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  FAILED: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
}

export const DATA_PLAN_STEP_TYPE_LABELS: Record<string, string> = {
  SEED: '数据种子',
  TRANSFORM: '转换',
  BACKUP: '备份',
  SNAPSHOT: '快照',
  VERIFY: '校验',
  CLEANUP: '清理',
}

export const DATA_PLAN_STRATEGY_LABELS: Record<string, string> = {
  snapshot_restore: '快照恢复',
  reseed: '重新灌数',
  incremental: '增量更新',
  synthetic: '合成数据',
  audit_trail: '审计轨迹',
}
