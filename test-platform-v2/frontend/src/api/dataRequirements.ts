import { aitdeV2 } from './missions'

// ── AITDE V3.2 Data + DB Runtime: Data Requirement domain ──

export interface DataRequirement {
  id: number
  scenario_version_id: number
  requirement_key: string
  entity_type: string
  constraints_json: Record<string, unknown> | null
  required: boolean
  sharing_policy: string | null
  cleanup_policy: string | null
  source_refs_json: Record<string, unknown> | null
  created_at: string | null
}

export interface UpdateDataRequirementInput {
  entity_type?: string
  constraints?: Record<string, unknown>
  required?: boolean
  sharing_policy?: string
  cleanup_policy?: string
}

export function fetchDataRequirements(
  scenarioVersionId: number,
  signal?: AbortSignal,
): Promise<DataRequirement[]> {
  return aitdeV2.get(`/scenarios/${scenarioVersionId}/data-requirements`, { signal })
}

export function deriveDataRequirements(scenarioVersionId: number): Promise<DataRequirement[]> {
  return aitdeV2.post(`/scenarios/${scenarioVersionId}/data-requirements/derive`)
}

export function updateDataRequirement(
  requirementId: number,
  payload: UpdateDataRequirementInput,
): Promise<DataRequirement> {
  return aitdeV2.patch(`/data-requirements/${requirementId}`, payload)
}
