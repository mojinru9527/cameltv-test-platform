import api from './client'
import type {
  WikiConfig,
  WikiRawSource,
  LanhuImportRequest,
  LanhuImportResult,
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

export type {
  WikiConfig,
  WikiRawSource,
  LanhuImportRequest,
  LanhuImportResult,
} from '@/types'
