import client from './client'

/** batch-337（P1）：AIQE Console —— Execution Profile / Workflow 审批 API 客户端。 */

export interface ExecutionProfile {
  id: string
  name: string
  purpose: string
  version: number
  approval_status: string
  checksum: string
  owner_id: number | null
  frozen: boolean
}

export interface WorkflowSummary {
  id: string
  scenario_id: number | null
  version: number
  schema_version: string
  checksum: string
  validation_status: string
  approval_status: string
  approved_by: number | null
  approved_at: string | null
  created_at: string
  node_count: number
  frozen: boolean
}

export interface WorkflowDetail extends WorkflowSummary {
  graph_json: Record<string, unknown>
}

export async function listProfiles(): Promise<ExecutionProfile[]> {
  return (await client.get('/aiqe/admin/profiles')) as unknown as ExecutionProfile[]
}

export async function createProfile(body: {
  name: string
  purpose: string
  config?: Record<string, unknown>
}): Promise<ExecutionProfile> {
  return (await client.post('/aiqe/admin/profiles', body)) as unknown as ExecutionProfile
}

export async function approveProfile(profileId: string): Promise<ExecutionProfile> {
  return (await client.post(
    `/aiqe/admin/profiles/${profileId}/approve`,
  )) as unknown as ExecutionProfile
}

export async function listWorkflows(params: {
  approval_status?: string
  limit?: number
  offset?: number
} = {}): Promise<{ items: WorkflowSummary[]; total: number }> {
  return (await client.get('/aiqe/workflows', {
    params,
  })) as unknown as { items: WorkflowSummary[]; total: number }
}

export async function getWorkflow(workflowId: string): Promise<WorkflowDetail> {
  return (await client.get(`/aiqe/workflows/${workflowId}`)) as unknown as WorkflowDetail
}

export async function approveWorkflow(workflowId: string): Promise<WorkflowSummary> {
  return (await client.post(
    `/aiqe/workflows/${workflowId}/approve`,
  )) as unknown as WorkflowSummary
}

// ── batch-338：QualityGate / NoiseRules ──

export interface QualityGateResult {
  gate_status: 'PASS' | 'FAIL' | 'BLOCKED'
  p0_total: number
  p0_passed: number
  p0_failed: number
  p0_unknown: number
  p0_not_run: number
  reasons: string[]
}

export interface NoiseRule {
  id: number
  pattern: string
  action: string
  scope: string
  expires_at: string
  status: string
  effective: boolean
}

export async function evaluateQualityGate(body: {
  p0_total: number
  p0_passed: number
  p0_failed: number
  p0_unknown: number
  p0_not_run: number
}): Promise<QualityGateResult> {
  return (await client.post('/aiqe/admin/quality-gate', body)) as unknown as QualityGateResult
}

export async function listNoiseRules(): Promise<NoiseRule[]> {
  return (await client.get('/aiqe/admin/noise-rules')) as unknown as NoiseRule[]
}

export async function createNoiseRule(body: {
  pattern: string
  action?: string
  scope?: string
  expires_at?: string
}): Promise<NoiseRule> {
  return (await client.post('/aiqe/admin/noise-rules', body)) as unknown as NoiseRule
}

export async function renewNoiseRule(ruleId: number): Promise<NoiseRule> {
  return (await client.post(
    `/aiqe/admin/noise-rules/${ruleId}/renew`,
  )) as unknown as NoiseRule
}

export async function deleteNoiseRule(ruleId: number): Promise<void> {
  await client.delete(`/aiqe/admin/noise-rules/${ruleId}`)
}

// ── batch-339：平台矩阵（真实节点能力） ──

export interface PlatformMatrixCell {
  available: boolean
  node_count: number
  nodes: string[]
}

export interface PlatformMatrixNode {
  node_id: string
  driver_key: string
  driver_version: string
  platforms: string[]
  capabilities: string[]
  available: boolean
  last_evidence_ref: string
  last_heartbeat_at: string | null
}

export interface PlatformMatrix {
  platforms: string[]
  capabilities: string[]
  rows: { capability: string; cells: Record<string, PlatformMatrixCell> }[]
  nodes: PlatformMatrixNode[]
  available_nodes: number
}

export async function getPlatformMatrix(): Promise<PlatformMatrix> {
  return (await client.get('/aiqe/platform-matrix')) as unknown as PlatformMatrix
}
