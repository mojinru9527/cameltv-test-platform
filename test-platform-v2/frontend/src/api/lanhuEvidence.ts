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
  quality_json: string
  error_message: string
  attempt_no: number
  parent_job_id?: number | null
  import_result_json: string
  requested_options_json?: string
  heartbeat_at?: string | null
  created_at?: string | null
  finished_at?: string | null
}

export interface LanhuEvidenceQuality {
  page_count?: number
  complete?: boolean
  import_ready?: boolean
  pages_missing_capture?: number[]
  pages_truncated?: number[]
  pages_missing_text?: number[]
  pages_missing_ocr_review?: number[]
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
  capture_truncated: boolean
  dom_text: string
  ocr_text: string
  merged_text: string
  quality_json: string
  error_message: string
  review_status: 'pending' | 'approved' | 'rejected' | string
  review_comment: string
  reviewed_at?: string | null
}

export interface LanhuEvidenceAsset {
  id: number
  job_id: number
  page_id?: number | null
  asset_type: 'screenshot' | 'word' | 'json' | 'other' | string
  relative_path: string
  mime_type: string
  width: number
  height: number
  scroll_top: number
  viewport_height: number
  sha256: string
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

export interface LanhuEvidencePageReviewRequest {
  approved: boolean
  comment: string
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

export async function fetchLanhuEvidenceAssets(jobId: number): Promise<LanhuEvidenceAsset[]> {
  return api.get(`/lanhu-evidence/jobs/${jobId}/assets`)
}

export async function reviewLanhuEvidencePage(
  pageId: number,
  body: LanhuEvidencePageReviewRequest,
): Promise<LanhuEvidencePage> {
  return api.post(`/lanhu-evidence/pages/${pageId}/review`, body)
}

export async function downloadLanhuEvidenceAsset(assetId: number): Promise<Blob> {
  return api.get(`/lanhu-evidence/assets/${assetId}`, { responseType: 'blob' })
}

export async function cancelLanhuEvidenceJob(jobId: number): Promise<LanhuEvidenceJob> {
  return api.post(`/lanhu-evidence/jobs/${jobId}/cancel`, {})
}

export async function retryLanhuEvidenceJob(jobId: number): Promise<LanhuEvidenceJob> {
  return api.post(`/lanhu-evidence/jobs/${jobId}/retry`, {})
}

export async function deleteLanhuEvidenceJob(jobId: number): Promise<{ deleted: boolean; job_id: number }> {
  return api.delete(`/lanhu-evidence/jobs/${jobId}`)
}

export async function importLanhuEvidence(
  jobId: number,
  body: LanhuEvidenceImportRequest,
): Promise<Record<string, unknown>> {
  return api.post(`/lanhu-evidence/jobs/${jobId}/import`, body)
}
