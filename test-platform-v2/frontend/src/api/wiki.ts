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

export type {
  WikiConfig,
  WikiRawSource,
  LanhuImportRequest,
  LanhuImportResult,
  WikiIngestJob,
  WikiPageBrief,
  WikiPage,
  WikiLink,
} from '@/types'
