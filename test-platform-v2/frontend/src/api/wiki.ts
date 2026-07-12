import api from './client'
import type {
  WikiConfig,
  WikiRawSource,
  LanhuImportRequest,
  LanhuImportResult,
  WikiIngestJob,
  WikiPageBrief,
  WikiPage,
  WikiLink,
  WikiDiffTaskBrief,
  WikiDiffTask,
  WikiDiffItem,
  WikiDiffCreateRequest,
  WikiDiffCreateArtifactResult,
  KnowledgePage,
} from '@/types'

// ── 配置 / 开关 ──

export async function fetchWikiConfig(): Promise<WikiConfig> {
  return api.get('/wiki/config')
}

// ── Raw Source / 蓝湖导入 (VNext-1) ──

export async function importLanhu(body: LanhuImportRequest): Promise<LanhuImportResult> {
  return api.post('/wiki/import/lanhu', body)
}

export async function fetchWikiRawSources(params: {
  source_type?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<KnowledgePage<WikiRawSource>> {
  return api.get('/wiki/raw-sources', { params })
}

export async function fetchWikiRawSource(id: number): Promise<WikiRawSource> {
  return api.get(`/wiki/raw-sources/${id}`)
}

// ── Wiki 编译任务 (VNext-2) ──

export async function createWikiIngestJob(raw_source_id: number): Promise<WikiIngestJob> {
  return api.post('/wiki/ingest-jobs', { raw_source_id })
}

export async function fetchWikiIngestJob(jobId: number): Promise<WikiIngestJob> {
  return api.get(`/wiki/ingest-jobs/${jobId}`)
}

export async function retryWikiIngestJob(jobId: number): Promise<WikiIngestJob> {
  return api.post(`/wiki/ingest-jobs/${jobId}/retry`, {})
}

export async function cancelWikiIngestJob(jobId: number): Promise<WikiIngestJob> {
  return api.post(`/wiki/ingest-jobs/${jobId}/cancel`, {})
}

// ── Wiki 页面 (VNext-2) ──

export async function fetchWikiPages(params: {
  page_type?: string
  review_status?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<KnowledgePage<WikiPageBrief>> {
  return api.get('/wiki/pages', { params })
}

export async function fetchWikiPage(pageId: number): Promise<WikiPage> {
  return api.get(`/wiki/pages/${pageId}`)
}

export async function fetchWikiPageLinks(pageId: number): Promise<WikiLink[]> {
  return api.get(`/wiki/pages/${pageId}/links`)
}

export async function searchWikiPages(keyword: string): Promise<KnowledgePage<WikiPageBrief>> {
  return api.get('/wiki/search', { params: { keyword } })
}

export async function approveWikiPage(pageId: number, comment = ''): Promise<WikiPage> {
  return api.post(`/wiki/pages/${pageId}/approve`, { comment })
}

export async function rejectWikiPage(pageId: number, comment = ''): Promise<WikiPage> {
  return api.post(`/wiki/pages/${pageId}/reject`, { comment })
}

// ── 知识库差异对比 (VNext-3) ──

export async function createWikiDiffTask(body: WikiDiffCreateRequest): Promise<WikiDiffTask> {
  return api.post('/wiki/diff/tasks', body)
}

export async function fetchWikiDiffTasks(params?: {
  status?: string; page?: number; page_size?: number
}): Promise<KnowledgePage<WikiDiffTaskBrief>> {
  return api.get('/wiki/diff/tasks', { params })
}

export async function fetchWikiDiffTask(taskId: number, filters?: {
  dimension?: string; diff_type?: string; severity?: string; review_status?: string
}): Promise<WikiDiffTask> {
  return api.get(`/wiki/diff/tasks/${taskId}`, { params: filters })
}

export async function acceptWikiDiffItem(itemId: number): Promise<WikiDiffItem> {
  return api.post(`/wiki/diff/items/${itemId}/accept`, {})
}

export async function rejectWikiDiffItem(itemId: number): Promise<WikiDiffItem> {
  return api.post(`/wiki/diff/items/${itemId}/reject`, {})
}

export async function createWikiDiffArtifact(itemId: number, artifact_type = ''): Promise<WikiDiffCreateArtifactResult> {
  return api.post(`/wiki/diff/items/${itemId}/create-artifact`, { artifact_type })
}

export type {
  WikiConfig,
  WikiRawSource,
  LanhuImportRequest,
  LanhuImportResult,
  WikiIngestJob,
  WikiPageBrief,
  WikiPage,
  WikiLink,
  WikiDiffTaskBrief,
  WikiDiffTask,
  WikiDiffItem,
  WikiDiffCreateRequest,
} from '@/types'
