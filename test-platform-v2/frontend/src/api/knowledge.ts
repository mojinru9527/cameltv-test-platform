import api from './client'
import type {
  KnowledgeChunk,
  KnowledgeOverview,
  KnowledgePage,
  KnowledgeSearchQuery,
  KnowledgeSearchResult,
  KnowledgeSource,
  ReembedResult,
  SearchHealth,
} from '@/types'

// 说明：axios 拦截器已拆包 {code,msg,data}，并自动附带 X-Project-Id 头，
// 因此这里返回的即是 data，无需再传 project_id。

export async function fetchKnowledgeOverview(signal?: AbortSignal): Promise<KnowledgeOverview> {
  if (signal) return api.get('/knowledge/overview', { signal })
  return api.get('/knowledge/overview')
}

export interface VersionKnowledgeRecord {
  id: number
  task_id: number
  version: string
  title: string
  summary: string
  coverage: { pass?: number; fail?: number; skip?: number; blocked?: number }
  verdict: string
  risk: unknown
  plan_summary: unknown
  defect_count: number
  created_at: string | null
}

export async function fetchVersionKnowledge(signal?: AbortSignal): Promise<VersionKnowledgeRecord[]> {
  return api.get('/knowledge/version-records', signal ? { signal } : undefined)
}

export async function fetchKnowledgeSources(params: {
  source_type?: string
  para_category?: string
  knowledge_domain?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<KnowledgePage<KnowledgeSource>> {
  return api.get('/knowledge/sources', { params })
}

export async function fetchKnowledgeSource(id: number): Promise<KnowledgeSource> {
  return api.get(`/knowledge/sources/${id}`)
}

export async function fetchSourceChunks(sourceId: number): Promise<KnowledgeChunk[]> {
  return api.get(`/knowledge/sources/${sourceId}/chunks`)
}

export async function verifyKnowledgeSource(sourceId: number): Promise<KnowledgeSource> {
  return api.post(`/knowledge/sources/${sourceId}/verify`)
}

export async function classifyKnowledgeSource(
  sourceId: number,
  body: { para_category?: string; knowledge_domain?: string },
): Promise<KnowledgeSource> {
  return api.patch(`/knowledge/sources/${sourceId}/classify`, body)
}

// ── M2 混合检索 ──

export async function searchKnowledge(
  body: KnowledgeSearchQuery,
): Promise<KnowledgeSearchResult[]> {
  return api.post('/knowledge/search', body)
}

export async function reembedKnowledge(): Promise<ReembedResult> {
  return api.post('/knowledge/reembed')
}

export async function fetchSearchHealth(): Promise<SearchHealth> {
  return api.get('/knowledge/search/health')
}

// ── 灵感捕获 ──

export async function captureInsight(body: {
  title: string
  content: string
  source_url?: string
  tags?: string[]
}): Promise<{ id: number; title: string; status: string }> {
  return api.post('/knowledge/capture', body)
}
