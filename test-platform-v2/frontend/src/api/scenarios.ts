import { aitdeV2 } from './missions'

export interface ScenarioRow {
  id: number
  scenario_key: string
  title: string
  priority: string
  risk_level: string
  review_status: 'PROPOSED' | 'APPROVED' | 'REJECTED' | 'REQUEST_CHANGE' | string
  version_no: number
  oracle_count: number
}

export interface Oracle {
  id: number
  oracle_key: string
  oracle_type: string
  target: Record<string, unknown>
  operator: string
  expected_value: Record<string, unknown>
  source_type: string
  required: boolean
  confidence: number
  review_status: string
}

export interface ScenarioDetail {
  id: number
  scenario_key: string
  version_no: number
  scenario_version_id: number
  title: string
  business_goal: string
  priority: string
  risk_level: string
  given_model: Record<string, unknown>
  when_model: Record<string, unknown>
  expected_state: Record<string, unknown>
  review_status: string
  oracles: Oracle[]
}

export interface FunctionalProjection {
  scenario_key: string
  title: string
  priority: string
  preconditions: string[]
  steps: { step: number; description: string }[]
  expected_results: string[]
}

export function generateScenarios(contractVersionId: number): Promise<{ contract_version_id: number; scenario_count: number }> {
  return aitdeV2.post(`/contracts/${contractVersionId}/scenarios/generate`)
}

export function fetchMissionScenarios(missionId: number): Promise<ScenarioRow[]> {
  return aitdeV2.get(`/missions/${missionId}/scenarios`)
}

export function fetchScenario(scenarioId: number): Promise<ScenarioDetail> {
  return aitdeV2.get(`/scenarios/${scenarioId}`)
}

export function reviewScenario(
  scenarioId: number,
  action: 'approve' | 'reject' | 'request_change',
): Promise<{ scenario_id: number; review_status: string }> {
  return aitdeV2.post(`/scenarios/${scenarioId}/review`, { action })
}

export function fetchFunctionalProjection(scenarioId: number): Promise<FunctionalProjection> {
  return aitdeV2.get(`/scenarios/${scenarioId}/functional-projection`)
}

export const SCENARIO_REVIEW_LABELS: Record<string, { label: string; color: string }> = {
  PROPOSED: { label: '待评审', color: 'bg-status-warning-muted text-status-warning' },
  APPROVED: { label: '已批准', color: 'bg-status-success-muted text-status-success' },
  REJECTED: { label: '已拒绝', color: 'bg-status-danger-muted text-status-danger' },
  REQUEST_CHANGE: { label: '需修改', color: 'bg-status-warning-muted text-status-warning' },
}
