import client from './client'

export interface AiqeContractSummary {
  id: string
  requirement_id: string
  revision: number
  title: string
  status: string
  revision_checksum: string
  created_at: string
}

export interface AiqeAcceptanceCriterion {
  ac_id: string
  priority: string
  oracle_type: string
  oracle_ref: string
  platforms: string[]
  approval_status: string
}

export interface AiqeContractDetail extends AiqeContractSummary {
  project_id: number
  business_goal: string
  actors: string[]
  source_refs: string[]
  ambiguities: Array<Record<string, string>>
  acceptance_criteria: AiqeAcceptanceCriterion[]
  approved_by: number | null
  frozen_at: string | null
}

export interface AiqeCaseSummary {
  case_id: string
  title: string
  priority: string
  automation_grade: string
  review_status: string
  contract_id: string | null
  contract_revision: number | null
  covers_ac_ids: string[]
  platform_targets: string[]
  oracle_ref: string
}

export interface AiqeCoverageReport {
  contract_id: string
  coverage: Record<string, string>
  uncovered: string[]
  partial: string[]
}

interface PageData<T> {
  items: T[]
  total: number
}

export async function listContracts(params: {
  requirement_id?: string
  status?: string
  limit?: number
} = {}): Promise<AiqeContractSummary[]> {
  const data = (await client.get('/aiqe/contracts', { params })) as unknown as PageData<AiqeContractSummary>
  return data.items
}

export async function getContract(contractId: string): Promise<AiqeContractDetail> {
  return (await client.get(`/aiqe/contracts/${contractId}`)) as unknown as AiqeContractDetail
}

export async function createContract(payload: {
  requirement_id: string
  title: string
  business_goal?: string
  source_refs?: string[]
  acceptance_criteria?: Array<Record<string, unknown>>
}): Promise<AiqeContractDetail> {
  return (await client.post('/aiqe/contracts', payload)) as unknown as AiqeContractDetail
}

export async function transitionContract(contractId: string, target: string): Promise<AiqeContractDetail> {
  return (await client.post(`/aiqe/contracts/${contractId}/transition`, {
    target,
  })) as unknown as AiqeContractDetail
}

export async function approveAc(contractId: string, acId: string): Promise<{ ac_id: string; approval_status: string }> {
  return (await client.post(`/aiqe/contracts/${contractId}/approve-ac`, {
    ac_id: acId,
  })) as unknown as { ac_id: string; approval_status: string }
}

export async function getContractCoverage(contractId: string): Promise<AiqeCoverageReport> {
  return (await client.get(`/aiqe/contracts/${contractId}/coverage`)) as unknown as AiqeCoverageReport
}

export async function listCases(params: {
  contract_id?: string
  review_status?: string
  priority?: string
  limit?: number
} = {}): Promise<AiqeCaseSummary[]> {
  const data = (await client.get('/aiqe/cases', { params })) as unknown as PageData<AiqeCaseSummary>
  return data.items
}

export async function reviewCase(caseId: string, decision: 'APPROVED' | 'REJECTED'): Promise<AiqeCaseSummary> {
  return (await client.post(`/aiqe/cases/${caseId}/review`, { decision })) as unknown as AiqeCaseSummary
}
