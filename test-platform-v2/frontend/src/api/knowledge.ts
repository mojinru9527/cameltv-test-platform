import api from './client'
import type {
  AiArtifact,
  EntityExtractResult,
  GraphView,
  KnowledgeChunk,
  KnowledgeEntityBrief,
  KnowledgeEntity,
  KnowledgeOverview,
  KnowledgePage,
  KnowledgeRelation,
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

export async function triggerEntityExtract(sourceId?: number | null, maxChunks = 100): Promise<EntityExtractResult> {
  return api.post('/knowledge/graph/extract', { source_id: sourceId ?? null, max_chunks: maxChunks })
}

export async function fetchEntities(params: {
  entity_type?: string
  keyword?: string
  limit?: number
}): Promise<KnowledgeEntityBrief[]> {
  return api.get('/knowledge/graph/entities', { params })
}

export async function fetchEntityDetail(id: number): Promise<KnowledgeEntity> {
  return api.get(`/knowledge/graph/entities/${id}`)
}

export async function fetchRelations(params: {
  entity_id?: number
  relation_type?: string
  limit?: number
}): Promise<KnowledgeRelation[]> {
  return api.get('/knowledge/graph/relations', { params })
}

export async function approveRelation(id: number, comment?: string): Promise<KnowledgeRelation> {
  return api.post(`/knowledge/graph/relations/${id}/approve`, { comment: comment ?? '' })
}

export async function rejectRelation(id: number, comment?: string): Promise<KnowledgeRelation> {
  return api.post(`/knowledge/graph/relations/${id}/reject`, { comment: comment ?? '' })
}
