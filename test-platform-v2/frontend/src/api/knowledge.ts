import api from './client'
import type {
  AiArtifact,
  GraphView,
  KnowledgeChunk,
  KnowledgeOverview,
  KnowledgePage,
  KnowledgeSearchQuery,
  KnowledgeSearchResult,
  KnowledgeSource,
  ReembedResult,
} from '@/types'

// 说明：axios 拦截器已拆包 {code,msg,data}，并自动附带 X-Project-Id 头，
// 因此这里返回的即是 data，无需再传 project_id。

export async function fetchKnowledgeOverview(): Promise<KnowledgeOverview> {
  return api.get('/knowledge/overview')
}

export async function fetchKnowledgeSources(params: {
  source_type?: string
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

export async function fetchAiArtifacts(params: {
  review_status?: string
  artifact_type?: string
  page?: number
  page_size?: number
}): Promise<KnowledgePage<AiArtifact>> {
  return api.get('/knowledge/ai-artifacts', { params })
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

// ── M3 知识图谱 ──

export async function fetchGraphView(limit = 200): Promise<GraphView> {
  return api.get('/knowledge/graph/view', { params: { limit } })
}

export async function triggerEntityExtract(sourceId?: number | null, maxChunks = 100): Promise<{ extracted: number; relations: number; skipped: number; message: string }> {
  return api.post('/knowledge/graph/extract', { source_id: sourceId, max_chunks: maxChunks })
}
