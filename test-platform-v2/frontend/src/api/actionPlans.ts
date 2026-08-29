import { aitdeV2 } from './missions'
import { parseJson } from './json'

// ── AITDE V3.3 Browser + Hybrid + Assisted Manual: Action Plan (Command IR) ──

/** A single Command IR command. Drivers: browser / data / api / assertion. */
export interface CommandIRCommand {
  id: string
  driver: string
  action: string
  input: Record<string, unknown>
  observation_ref?: string
}

/** Command IR payload: the ordered instruction set that drives the runtime. */
export interface CommandIR {
  schema_version: string
  commands: CommandIRCommand[]
}

export interface ActionPlanVersion {
  id: number
  command_plan_id: number
  version_no: number
  scenario_version_id: number
  contract_version_id: number
  schema_version: string
  /** Backend stores the Command IR as a JSON string; parsed here. */
  plan_json: CommandIR | null
  plan_hash: string
  status: string
  generated_by_type: string
  model_ref: string | null
  prompt_version: string | null
  created_at: string | null
  approved_by: number | null
  approved_at: string | null
}

export interface ValidateActionPlanResult {
  valid: boolean
  errors: unknown[]
}

export interface GenerateActionPlanInput {
  scenario_version_id: number
  contract_version_id: number
  plan: CommandIR
  schema_version?: string
  model_ref?: string
  prompt_version?: string
}

type RawActionPlanVersion = Omit<ActionPlanVersion, 'plan_json'> & {
  plan_json?: string | null
}

function mapVersion(raw: RawActionPlanVersion): ActionPlanVersion {
  return {
    ...raw,
    plan_json: parseJson<CommandIR>(raw.plan_json),
  }
}

export async function fetchActionPlans(
  scenarioId: number,
  signal?: AbortSignal,
): Promise<ActionPlanVersion[]> {
  const rows = (await aitdeV2.get(`/scenarios/${scenarioId}/action-plans`, { signal })) as RawActionPlanVersion[]
  return (rows ?? []).map(mapVersion)
}

export async function generateActionPlan(
  scenarioId: number,
  payload: GenerateActionPlanInput,
): Promise<ActionPlanVersion> {
  const raw = (await aitdeV2.post(`/scenarios/${scenarioId}/action-plans/generate`, payload)) as RawActionPlanVersion
  return mapVersion(raw)
}

export function validateActionPlan(versionId: number): Promise<ValidateActionPlanResult> {
  return aitdeV2.post(`/action-plans/${versionId}/validate`)
}

export function approveActionPlan(versionId: number): Promise<ActionPlanVersion> {
  return aitdeV2.post(`/action-plans/${versionId}/approve`)
}

// ── UI label/colour maps ──

export const ACTION_PLAN_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'bg-muted text-muted-foreground' },
  VALIDATED: { label: '已校验', color: 'bg-status-success-muted text-status-success' },
  APPROVED: { label: '已批准', color: 'bg-status-success-muted text-status-success' },
  INVALID: { label: '无效', color: 'bg-status-danger-muted text-status-danger' },
  REJECTED: { label: '已拒绝', color: 'bg-status-danger-muted text-status-danger' },
}

export const COMMAND_DRIVER_LABELS: Record<string, string> = {
  browser: '浏览器',
  data: '数据',
  api: 'API',
  assertion: '断言',
}
