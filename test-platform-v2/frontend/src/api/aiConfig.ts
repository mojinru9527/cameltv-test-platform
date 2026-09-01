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

/**
 * AI 提供方真实健康态（P0-2 / P2-6）。
 *
 * `configured` 只说明「填过提供方」，不代表 Key 可用：生产曾出现 Key 401
 * 但 AI 配置页 / DSH 页 / 需求页全部显示「已配置 / AI 可用」。
 * 后端据最近一次真实调用或连通性测试给出本字段。
 */
export interface AiHealth {
  /** ok=最近一次调用成功；error=最近一次失败；unknown=本进程尚未验证 */
  status: 'ok' | 'error' | 'unknown'
  /** 错误类别：unauthorized / quota / rate_limited / timeout / ... */
  kind: string
  /** 可直接展示的中文提示 */
  message: string
  provider_id: number | null
  checked_at: string | null
}

export interface AiResolveResult {
  configured: boolean
  provider: { id: number; name: string; model: string } | null
  health?: AiHealth
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

export async function testAiProviderConnection(id: number): Promise<{
  ok: boolean
  latency_ms?: number
  model?: string
  /** 可执行的中文提示（P2-7：不再回传原始 Python 异常串 + MDN 链接） */
  error?: string
  /** 错误类别，供 UI 决定是否给出「更新密钥」入口 */
  kind?: string
  /** 已脱敏的原始错误摘要（不含服务器路径），供展开排查 */
  detail?: string
}> {
  return api.post(`/ai-config/providers/${id}/test-connection`)
}

export async function fetchAiResolve(signal?: AbortSignal): Promise<AiResolveResult> {
  return api.get('/ai-config/resolve', { signal })
}

export async function discoverAiModels(
  body: { api_base_url: string; api_key: string },
): Promise<{ models: string[] }> {
  return api.post('/ai-config/providers/discover-models', body)
}
