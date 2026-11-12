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
