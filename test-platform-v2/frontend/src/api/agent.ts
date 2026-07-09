import api from './client'
import type { KnowledgePage } from '@/types'

// ── Agent 执行记录（后端返回 Page 包装） ──

export interface AgentRun {
  id: number
  project_id: number
  agent_type: string
  trigger_type: string
  input_json: string
  retrieved_context_json: string
  output_json: string
  status: string
  error_message: string
  duration_ms: number
  operator_id: number
  created_at: string | null
  finished_at: string | null
}

export interface AgentTypeMeta {
  type: string
  label: string
  description: string
  artifact_type: string
}

export interface AgentRunTriggerResult {
  run_id: number
  status: string
  message: string
}

export interface AgentRunPage {
  items: AgentRun[]
  total: number
  page: number
  page_size: number
}

export async function fetchAgentRuns(params: {
  agent_type?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<AgentRunPage> {
  return api.get('/agents/runs', { params })
}

export async function fetchAgentRun(id: number): Promise<AgentRun> {
  return api.get(`/agents/runs/${id}`)
}

export async function triggerAgent(
  agentType: string,
  query: string,
  params?: Record<string, any>,
): Promise<AgentRunTriggerResult> {
  return api.post(`/agents/run/${agentType}`, { query, params: params ?? {} })
}

export async function fetchAgentTypes(): Promise<AgentTypeMeta[]> {
  return api.get('/agents/types')
}
