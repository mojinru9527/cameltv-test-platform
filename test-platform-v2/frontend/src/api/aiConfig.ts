import api from './client'

// ── AI 模型配置中心（Batch A）：项目级提供方池 ──

export interface AiProviderItem {
  id: number
  name: string
  provider_type: string
  api_base_url: string
  api_key: string // 掩码（如 sk****cdef）
  models: string[]
  default_model: string
  is_default: boolean
  enabled: boolean
}

export interface AiResolveResult {
  configured: boolean
  provider: { id: number; name: string; model: string } | null
}

export async function fetchAiProviders(signal?: AbortSignal): Promise<AiProviderItem[]> {
  return api.get('/ai-config/providers', { signal })
}

export async function createAiProvider(body: Record<string, unknown>): Promise<{ id: number }> {
  return api.post('/ai-config/providers', body)
}

export async function updateAiProvider(id: number, body: Record<string, unknown>): Promise<{ id: number }> {
  return api.put(`/ai-config/providers/${id}`, body)
}

export async function deleteAiProvider(id: number): Promise<{ deleted: number }> {
  return api.delete(`/ai-config/providers/${id}`)
}

export async function testAiProviderConnection(id: number): Promise<{ ok: boolean; latency_ms?: number; model?: string; error?: string }> {
  return api.post(`/ai-config/providers/${id}/test-connection`)
}

export async function fetchAiResolve(signal?: AbortSignal): Promise<AiResolveResult> {
  return api.get('/ai-config/resolve', { signal })
}
