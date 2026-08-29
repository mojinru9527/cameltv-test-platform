import { aitdeV2 } from './missions'
import { parseJson, parseJsonArray } from './json'

// ── AITDE V3.2 Data + DB Runtime: Data Requirement domain ──

export interface DataRequirement {
  id: number
  scenario_version_id: number
  requirement_key: string
  entity_type: string
  /** Backend sends a JSON string; parsed to an object here. */
  constraints_json: Record<string, unknown> | null
  required: boolean
  sharing_policy: string | null
  cleanup_policy: string | null
  source_refs_json: Record<string, unknown>[] | null
  created_at: string | null
}

export interface UpdateDataRequirementInput {
  entity_type?: string
  constraints?: Record<string, unknown>
  required?: boolean
  sharing_policy?: string
  cleanup_policy?: string
}

interface RawDataRequirement extends Omit<DataRequirement, 'constraints_json' | 'source_refs_json'> {
  constraints_json?: string | null
  source_refs_json?: string | null
}

function mapRequirement(raw: RawDataRequirement): DataRequirement {
  return {
    ...raw,
    constraints_json: parseJson(raw.constraints_json),
    source_refs_json: parseJsonArray<Record<string, unknown>>(raw.source_refs_json),
  }
}

export async function fetchDataRequirements(
  scenarioVersionId: number,
  signal?: AbortSignal,
): Promise<DataRequirement[]> {
  const rows = (await aitdeV2.get(`/scenarios/${scenarioVersionId}/data-requirements`, { signal })) as RawDataRequirement[]
  return (rows ?? []).map(mapRequirement)
}

export async function deriveDataRequirements(scenarioVersionId: number): Promise<DataRequirement[]> {
  const rows = (await aitdeV2.post(`/scenarios/${scenarioVersionId}/data-requirements/derive`)) as RawDataRequirement[]
  return (rows ?? []).map(mapRequirement)
}

export function updateDataRequirement(
  requirementId: number,
  payload: UpdateDataRequirementInput,
): Promise<DataRequirement> {
  return aitdeV2.patch(`/data-requirements/${requirementId}`, payload)
}
