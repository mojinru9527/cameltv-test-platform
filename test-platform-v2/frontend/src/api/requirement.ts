import api from './client'
import type {
  AIGenerateResult,
  ApiMatchItem,
  FeatureExtractionResult,
  ExtractionConfirmRequest,
  RequirementDocument,
} from '@/types'

export async function fetchRequirements(): Promise<RequirementDocument[]> {
  return api.get('/requirements')
}

export async function uploadRequirement(data: FormData): Promise<RequirementDocument> {
  return api.post('/requirements/upload', data)
}

export async function extractFeatures(documentId: number): Promise<FeatureExtractionResult> {
  return api.post(`/requirements/${documentId}/extract`)
}

export async function getExtraction(documentId: number): Promise<FeatureExtractionResult> {
  return api.get(`/requirements/${documentId}/extraction`)
}

export async function confirmExtraction(
  documentId: number,
  data: ExtractionConfirmRequest
): Promise<Record<string, unknown>> {
  return api.post(`/requirements/${documentId}/extraction/confirm`, data)
}

export async function generateTestCases(
  documentId: number,
  options?: { use_extraction?: boolean }
): Promise<AIGenerateResult> {
  return api.post(`/requirements/${documentId}/generate`, options || {})
}

export async function importCases(
  documentId: number,
  indices: number[]
): Promise<{ imported: number; skipped: number; total: number }> {
  return api.post(`/requirements/${documentId}/import`, { indices })
}

export async function fetchGeneratedCases(documentId: number): Promise<AIGenerateResult> {
  return api.get(`/requirements/${documentId}/cases`)
}

export async function deleteRequirement(documentId: number): Promise<void> {
  return api.delete(`/requirements/${documentId}`)
}

// ── Review queue ──

export interface ReviewState {
  document_title: string
  functional_cases: ReviewCaseItem[]
  api_cases: ReviewCaseItem[]
  summary: {
    total: number
    approved: number
    rejected: number
    pending: number
  }
}

export interface ReviewCaseItem {
  index: number
  title: string
  priority: string
  module: string
  domain: string
  preconditions: string
  steps: string
  expected_result: string
  case_type: string
  review_status: string
  edited_data: Record<string, unknown> | null
  imported: boolean
}

export async function fetchReviewState(documentId: number): Promise<ReviewState> {
  return api.get(`/requirements/${documentId}/review-state`)
}

export async function reviewCase(
  documentId: number,
  caseIndex: number,
  action: 'approve' | 'reject',
): Promise<Record<string, unknown>> {
  return api.post(`/requirements/${documentId}/review/${caseIndex}`, { action })
}

export { importCases as reviewImportCases }

// ── API endpoint matching (batch-34) ──

export async function matchApiEndpoints(documentId: number): Promise<ApiMatchItem[]> {
  return api.post(`/requirements/${documentId}/match-api`)
}
