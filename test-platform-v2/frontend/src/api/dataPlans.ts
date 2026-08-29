import { aitdeV2 } from './missions'
import { parseJson } from './json'

// ── AITDE V3.2 Data + DB Runtime: Data Plan domain ──

export interface DataPlanStep {
  id: number
  sequence: number
  step_type: string
  driver: string
  /** Backend sends JSON strings; parsed to objects here. */
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

interface RawDataPlanStep extends Omit<DataPlanStep, 'command_json' | 'compensation_json'> {
  command_json?: string | null
  compensation_json?: string | null
}

interface RawDataPlan extends Omit<DataPlan, 'steps'> {
  steps?: RawDataPlanStep[]
}

function mapStep(raw: RawDataPlanStep): DataPlanStep {
  return {
    ...raw,
    command_json: parseJson(raw.command_json),
    compensation_json: parseJson(raw.compensation_json),
  }
}

function mapPlan(raw: RawDataPlan): DataPlan {
  return {
    ...raw,
    steps: (raw.steps ?? []).map(mapStep),
  }
}

export async function createDataPlan(
  scenarioVersionId: number,
  payload: CreateDataPlanInput = {},
): Promise<DataPlan> {
  const raw = (await aitdeV2.post(`/scenarios/${scenarioVersionId}/data-plans`, payload)) as RawDataPlan
  return mapPlan(raw)
}

export async function fetchDataPlan(planId: number, signal?: AbortSignal): Promise<DataPlan> {
  const raw = (await aitdeV2.get(`/data-plans/${planId}`, { signal })) as RawDataPlan
  return mapPlan(raw)
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
  FIND: '查找',
  CREATE: '创建',
  UPDATE: '更新',
  VERIFY: '校验',
  LEASE: '租约',
  SNAPSHOT: '快照',
  CLEANUP: '清理',
}

export const DATA_PLAN_STRATEGY_LABELS: Record<string, string> = {
  EXISTING: '已有数据',
  API_BUILDER: 'API 构造',
  DB_FIXTURE: 'DB 夹具',
  WORKFLOW: '业务流',
}
