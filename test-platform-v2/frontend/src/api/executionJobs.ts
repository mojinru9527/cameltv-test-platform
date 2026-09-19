import api from './client'

/**
 * 本地执行节点（Batch 258 / B1-5、B1-6）。
 *
 * 平台的**控制面只做登记 · 调度 · 证据 · 知识**：接口与 Web 用例的真实执行发生在
 * 测试人员本机的 `cameltv-node` 里（ADR-0026 / 09-platform-landing-plan.md §3.1）。
 * 因此这里回答的问题是「为什么我点了没反应」——没有节点时，必须明确说出来。
 */

export interface ExecutionNode {
  node_id: string
  status: string
  capabilities: string[]
  last_health_at: string | null
}

export interface NodeStatus {
  online_nodes: number
  queue_length: number
  running_jobs: number
  stalled_jobs: number
  nodes: ExecutionNode[]
}

/**
 * 轮询间隔。backlog B1-6 的 DoD 是「节点上线后 10s 内状态刷新」，
 * 取 8s 留出网络与渲染余量；改动此值必须同步更新 __tests__ 里的断言。
 */
export const NODE_STATUS_POLL_MS = 8000

export async function fetchNodeStatus(signal?: AbortSignal): Promise<NodeStatus> {
  return api.get('/execution-jobs/node-status', { signal })
}

export interface ExecutionJobItem {
  id: number
  kind: string
  status: string
  attempt: number
  env_ref: string
  summary: string
  created_at: string | null
}

export interface ExecutionJobList {
  items: ExecutionJobItem[]
  total: number
}

export async function fetchExecutionJobs(
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<ExecutionJobList> {
  return api.get('/execution-jobs', { params, signal })
}

/** 证据包校验结果（Batch 261 / B4-1）。 */
export interface EvidenceFileStatus {
  name: string
  evidence_type: string | null
  status: 'ok' | 'tampered' | 'missing'
  expected_sha256?: string
  actual_sha256?: string | null
}

export interface EvidenceVerification {
  job_id: number
  attempt: number
  verdict: 'verified' | 'tampered' | 'missing' | 'incomplete'
  files: EvidenceFileStatus[]
  tampered: string[]
  missing: string[]
  extra: string[]
  unclassified: string[]
  completeness: { required: string[]; present: string[]; missing: string[]; complete: boolean }
  reason?: string
}

export async function verifyEvidenceBundle(
  jobId: number,
  attempt?: number,
  signal?: AbortSignal,
): Promise<EvidenceVerification> {
  return api.get(`/execution-jobs/${jobId}/evidence/verify`, {
    params: attempt ? { attempt } : {},
    signal,
  })
}

/** 一键启动指引：与 `scripts/node/README.md` 的命令保持一致。 */
export function nodeStartCommand(nodeId = 'my-pc'): string {
  return `cameltv-node up --node-id ${nodeId}`
}
