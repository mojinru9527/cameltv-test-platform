import { aitdeV2 } from './missions'

// ── AITDE V3.4 Durable Runtime domain types ──

export interface WorkerNode {
  id: number
  worker_key: string
  name: string
  network_zone: string
  status: string
  version: string
  machine_identity: string
  tags_json: Record<string, unknown> | string
  last_heartbeat_at: string | null
  registered_at: string | null
  capabilities?: string[]
}

export interface WorkerDetail extends WorkerNode {
  capabilities: string[]
}

export interface WorkflowRun {
  id: number
  project_id: number
  mission_id: number | null
  run_id: number | null
  workflow_type: string
  temporal_namespace: string
  temporal_workflow_id: string
  temporal_run_id: string | null
  status: string
  started_at: string | null
  closed_at: string | null
  created_at: string | null
}

export interface PolicyProfile {
  id: number
  project_id: number | null
  name: string
  policy_type: string
  version: string
  document_json: Record<string, unknown> | string
  status: string
  created_at: string | null
}

export interface SecretRef {
  id: number
  project_id: number
  name: string
  provider: string
  external_ref: string
  purpose: string
  scope_json: Record<string, unknown> | string
  status: string
  rotated_at: string | null
  created_at: string | null
}

export interface ApprovalRequest {
  id: number
  project_id: number
  mission_id: number | null
  run_id: number | null
  action_type: string
  request_json: Record<string, unknown> | string
  policy_decision: string
  status: string
  requested_by: number
  approved_by: number | null
  created_at: string | null
  resolved_at: string | null
}

export interface WorkersResult {
  items: WorkerNode[]
}

export interface WorkflowsResult {
  total: number
  page: number
  page_size: number
  items: WorkflowRun[]
}

export interface PolicyProfilesResult {
  items: PolicyProfile[]
}

export interface SecretRefsResult {
  items: SecretRef[]
}

export interface ApprovalsResult {
  items: ApprovalRequest[]
}

export interface WorkerHeartbeatInput {
  worker_key: string
  name?: string
  network_zone?: string
  version?: string
  machine_identity?: string
  tags?: Record<string, unknown>
  capabilities?: string[]
}

// ── Workers ──

export function fetchWorkers(signal?: AbortSignal): Promise<WorkersResult> {
  return aitdeV2.get('/workers', { signal })
}

export function fetchWorker(workerId: number, signal?: AbortSignal): Promise<WorkerDetail> {
  return aitdeV2.get(`/workers/${workerId}`, { signal })
}

export function drainWorker(workerId: number): Promise<WorkerDetail> {
  return aitdeV2.post(`/workers/${workerId}/drain`)
}

export function disableWorker(workerId: number): Promise<WorkerDetail> {
  return aitdeV2.post(`/workers/${workerId}/disable`)
}

export function heartbeatWorker(payload: WorkerHeartbeatInput): Promise<WorkerDetail> {
  return aitdeV2.post('/workers/heartbeat', payload)
}

// ── Workflows ──

export function fetchWorkflows(params: { page?: number; page_size?: number; signal?: AbortSignal }): Promise<WorkflowsResult> {
  const query: Record<string, string | number> = {}
  if (params.page != null) query.page = params.page
  if (params.page_size != null) query.page_size = params.page_size
  return aitdeV2.get('/workflows', { params: query, signal: params.signal })
}

export function resumeRun(runId: number, workflowId: string, signalName = 'resume'): Promise<Record<string, unknown>> {
  return aitdeV2.post(`/runs/${runId}/resume`, { workflow_id: workflowId, signal_name: signalName, args: {} })
}

// ── Policies ──

export function fetchPolicyProfiles(signal?: AbortSignal): Promise<PolicyProfilesResult> {
  return aitdeV2.get('/policy-profiles', { signal })
}

/** Evaluate a driver action against the policy gateway (returns decision). */
export function evaluatePolicy(payload: {
  actor?: string
  project_id?: number
  network_zone?: string
  driver: string
  action: string
  target?: Record<string, unknown>
}): Promise<{ decision: string; reason: string }> {
  return aitdeV2.post('/policy/evaluate', payload)
}

// ── Secret refs ──

export function fetchSecretRefs(signal?: AbortSignal): Promise<SecretRefsResult> {
  return aitdeV2.get('/secret-refs', { signal })
}

export function createSecretRef(payload: {
  name: string
  provider: string
  external_ref: string
  purpose?: string
  scope?: Record<string, unknown>
}): Promise<SecretRef> {
  return aitdeV2.post('/secret-refs', payload)
}

// ── Approvals ──

export function fetchApprovals(signal?: AbortSignal): Promise<ApprovalsResult> {
  return aitdeV2.get('/approvals', { signal })
}

export function approveApproval(approvalId: number, approvedBy = 0): Promise<ApprovalRequest> {
  return aitdeV2.post(`/approvals/${approvalId}/approve`, { approved_by: approvedBy })
}

export function rejectApproval(approvalId: number, approvedBy = 0): Promise<ApprovalRequest> {
  return aitdeV2.post(`/approvals/${approvalId}/reject`, { approved_by: approvedBy })
}

// ── Label maps ──

export const WORKER_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  ONLINE: { label: '在线', color: 'bg-status-success-muted text-status-success' },
  OFFLINE: { label: '离线', color: 'bg-muted text-muted-foreground' },
  DRAINING: { label: '排空中', color: 'bg-status-warning-muted text-status-warning' },
  DISABLED: { label: '已禁用', color: 'bg-status-danger-muted text-status-danger' },
}

export const WORKFLOW_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  WAITING_WORKER: { label: '等待Worker', color: 'bg-status-warning-muted text-status-warning' },
  WAITING_APPROVAL: { label: '等待审批', color: 'bg-status-warning-muted text-status-warning' },
  RETRYING: { label: '重试中', color: 'bg-status-info-muted text-status-info' },
  RESUMING: { label: '恢复中', color: 'bg-status-info-muted text-status-info' },
  SCHEDULED: { label: '已调度', color: 'bg-status-info-muted text-status-info' },
  RUNNING: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  FINISHED: { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  FAILED: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
  CANCELLED: { label: '已取消', color: 'bg-muted text-muted-foreground' },
}

export const APPROVAL_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PENDING: { label: '待审批', color: 'bg-status-warning-muted text-status-warning' },
  APPROVED: { label: '已批准', color: 'bg-status-success-muted text-status-success' },
  REJECTED: { label: '已拒绝', color: 'bg-status-danger-muted text-status-danger' },
  EXPIRED: { label: '已过期', color: 'bg-muted text-muted-foreground' },
}
