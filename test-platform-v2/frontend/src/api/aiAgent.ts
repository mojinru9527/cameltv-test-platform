import api from './client'

/**
 * 本地 AI Agent 控制面（Batch 248）。
 *
 * 平台不做 LLM 推理：这些接口只负责派发 AiJob、展示结果、把结果导入用例库。
 */

export type AiJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface AiJobItem {
  id: number
  project_id: number
  job_type: string
  status: AiJobStatus | string
  capability: string
  input_ref: string
  model_hint: string
  agent_id: string
  model_name: string
  summary: string
  payload: Record<string, unknown>
  evidence_refs: string[]
  error_message: string
  started_at: string | null
  finished_at: string | null
  created_at: string | null
}

export interface AiJobListResult {
  total: number
  page: number
  page_size: number
  items: AiJobItem[]
}

export interface AiAgentHealthItem {
  agent_id: string
  project_scope: number
  last_health_at: string | null
}

export async function fetchAiJobs(
  params: { status?: string; page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<AiJobListResult> {
  return api.get('/ai/jobs', { params, signal })
}

export async function fetchAiJob(jobId: number, signal?: AbortSignal): Promise<AiJobItem> {
  return api.get(`/ai/jobs/${jobId}`, { signal })
}

export async function fetchAiAgentHealth(
  signal?: AbortSignal,
): Promise<{ online: number; items: AiAgentHealthItem[] }> {
  return api.get('/ai/agents/health', { signal })
}

export async function importAiJobResult(
  jobId: number,
  indices?: number[],
): Promise<{ imported: number; skipped: number; total: number; already_imported: boolean }> {
  return api.post(`/ai/jobs/${jobId}/import`, indices && indices.length ? { indices } : {})
}
