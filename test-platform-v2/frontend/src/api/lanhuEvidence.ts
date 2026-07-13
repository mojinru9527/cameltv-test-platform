import api from './client'

// 蓝湖证据包 OCR 前端契约（对齐后端 /api/v1/lanhu-evidence/*）

export interface LanhuEvidenceCreateRequest {
  url: string
  capture_all_pages: boolean
  include_word: boolean
  include_json: boolean
  import_to_requirement: boolean
  import_to_knowledge: boolean
  import_to_wiki: boolean
}

export interface LanhuEvidenceJob {
  id: number
  project_id: number
  source_url: string
  doc_id: string
  version_id: string
  root_page_id: string
  document_name: string
  status: string
  stage: string
  total_pages: number
  captured_pages: number
  ocr_pages: number
  failed_pages: number
  word_path: string
  json_path: string
  quality_json: string
  error_message: string
  created_at?: string | null
  finished_at?: string | null
}

export interface LanhuEvidencePage {
  id: number
  job_id: number
  page_id: string
  page_name: string
  page_path: string
  folder: string
  order_index: number
  capture_status: string
  ocr_status: string
  segment_count: number
  dom_text: string
  ocr_text: string
  merged_text: string
  quality_json: string
  error_message: string
}

export interface LanhuEvidencePageList {
  total: number
  page: number
  page_size: number
  items: LanhuEvidencePage[]
}

export interface LanhuEvidenceJobList {
  total: number
  page: number
  page_size: number
  items: LanhuEvidenceJob[]
}

export interface LanhuEvidenceImportRequest {
  import_to_requirement: boolean
  import_to_knowledge: boolean
  import_to_wiki: boolean
}

export async function createLanhuEvidenceJob(
  body: LanhuEvidenceCreateRequest,
): Promise<LanhuEvidenceJob> {
  return api.post('/lanhu-evidence/jobs', body)
}

export async function fetchLanhuEvidenceJobs(params?: {
  page?: number
  page_size?: number
}): Promise<LanhuEvidenceJobList> {
  return api.get('/lanhu-evidence/jobs', { params })
}

export async function fetchLanhuEvidenceJob(jobId: number): Promise<LanhuEvidenceJob> {
  return api.get(`/lanhu-evidence/jobs/${jobId}`)
}

export async function fetchLanhuEvidencePages(jobId: number): Promise<LanhuEvidencePageList> {
  return api.get(`/lanhu-evidence/jobs/${jobId}/pages`)
}

export async function cancelLanhuEvidenceJob(jobId: number): Promise<LanhuEvidenceJob> {
  return api.post(`/lanhu-evidence/jobs/${jobId}/cancel`, {})
}

export async function retryLanhuEvidenceJob(jobId: number): Promise<LanhuEvidenceJob> {
  return api.post(`/lanhu-evidence/jobs/${jobId}/retry`, {})
}

export async function importLanhuEvidence(
  jobId: number,
  body: LanhuEvidenceImportRequest,
): Promise<Record<string, unknown>> {
  return api.post(`/lanhu-evidence/jobs/${jobId}/import`, body)
}
