import { aitdeV2 } from './missions'

export interface ContractRule {
  rule_key: string
  title?: string
  kind: string
  statement?: string
  risk_level?: string
  source_type?: string
}

export interface ContractOutcome {
  outcome_key: string
  statement?: string
  source_type?: string
}

export interface ContractSnapshot {
  schema_version: string
  mission_id: number
  scope_revision: string
  rules: ContractRule[]
  required_outcomes: ContractOutcome[]
}

export interface ContractVersion {
  id: number
  contract_id: number
  version_no: number
  status: 'DRAFT' | 'REVIEWING' | 'FROZEN' | 'SUPERSEDED' | string
  content_hash: string
  created_at: string | null
  approved_at: string | null
}

export interface CurrentContract {
  contract_id: number
  name: string
  version_no: number
  version: ContractVersion | null
}

export function generateContract(
  missionId: number,
  payload: { model?: string; force?: boolean } = {},
): Promise<{ contract_id: number; version_no: number; version_id: number }> {
  return aitdeV2.post(`/missions/${missionId}/contracts/generate`, payload)
}

export function fetchCurrentContract(missionId: number): Promise<CurrentContract> {
  return aitdeV2.get(`/missions/${missionId}/contract`)
}

export function fetchContractVersions(contractId: number): Promise<ContractVersion[]> {
  return aitdeV2.get(`/contracts/${contractId}/versions`)
}

export function freezeContract(
  contractId: number,
  expected_version: number,
): Promise<{ version_no: number; status: string; contract_id: number }> {
  return aitdeV2.post(`/contracts/${contractId}/freeze`, {
    expected_version,
    confirm: true,
  })
}

export const CONTRACT_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'bg-muted text-muted-foreground' },
  REVIEWING: { label: '评审中', color: 'bg-status-warning-muted text-status-warning' },
  FROZEN: { label: '已冻结', color: 'bg-status-success-muted text-status-success' },
  SUPERSEDED: { label: '已取代', color: 'bg-muted text-muted-foreground' },
}
