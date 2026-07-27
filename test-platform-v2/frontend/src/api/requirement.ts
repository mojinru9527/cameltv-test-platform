import api from './client'
import type {
  AIGenerateResult,
  ApiMatchItem,
  ApiMatchSelection,
  FeatureExtractionResult,
  ExtractionConfirmRequest,
  RequirementDocument,
  RequirementDocumentBrief,
  RequirementCoverage,
  AIGeneratedCase,
} from '@/types'
import type { KnowledgePage } from '@/types'

export async function fetchRequirements(params?: {
  page?: number
  page_size?: number
  keyword?: string
}, signal?: AbortSignal): Promise<KnowledgePage<RequirementDocumentBrief>> {
  return api.get('/requirements', { params, signal })
}

export async function fetchRequirement(
  documentId: number,
  signal?: AbortSignal,
): Promise<RequirementDocument> {
  return api.get(`/requirements/${documentId}`, { signal })
}

export async function fetchRequirementCoverage(
  documentId: number,
  signal?: AbortSignal,
): Promise<RequirementCoverage> {
  return api.get(`/requirements/${documentId}/coverage`, { signal })
}

export async function uploadRequirement(data: FormData): Promise<RequirementDocument> {
  return api.post('/requirements/upload', data)
}

export async function extractFeatures(
  documentId: number,
  signal?: AbortSignal,
): Promise<FeatureExtractionResult> {
  return api.post(`/requirements/${documentId}/extract`, undefined, { signal })
}

export async function getExtraction(
  documentId: number,
  signal?: AbortSignal,
): Promise<FeatureExtractionResult | null> {
  return api.get(`/requirements/${documentId}/extraction`, { signal })
}

export async function getOrCreateExtraction(
  documentId: number,
  signal?: AbortSignal,
): Promise<FeatureExtractionResult> {
  try {
    const existing = await getExtraction(documentId, signal)
    return existing === null ? extractFeatures(documentId, signal) : existing
  } catch (error) {
    const status = (
      typeof error === 'object'
      && error !== null
      && 'response' in error
    )
      ? (error as { response?: { status?: number } }).response?.status
      : undefined

    if (status === 404) {
      return extractFeatures(documentId, signal)
    }
    throw error
  }
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
  indices: number[],
  editedCases?: AIGeneratedCase[],
): Promise<{ imported: number; skipped: number; total: number }> {
  return api.post(`/requirements/${documentId}/import`, {
    indices,
    ...(editedCases && editedCases.length > 0 ? { edited_cases: editedCases } : {}),
  })
}

export async function fetchGeneratedCases(
  documentId: number,
  signal?: AbortSignal,
): Promise<AIGenerateResult> {
  return api.get(`/requirements/${documentId}/cases`, { signal })
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

export async function fetchReviewState(
  documentId: number,
  signal?: AbortSignal,
): Promise<ReviewState> {
  return api.get(`/requirements/${documentId}/review-state`, { signal })
}

export async function reviewCase(
  documentId: number,
  caseIndex: number,
  action: 'approve' | 'reject' | 'edit',
  editedData?: Partial<AIGeneratedCase>,
): Promise<Record<string, unknown>> {
  return api.post(`/requirements/${documentId}/review/${caseIndex}`, {
    action,
    ...(action === 'edit' ? { edited_data: editedData || {} } : {}),
  })
}

export { importCases as reviewImportCases }

// ── API endpoint matching (batch-34) ──

export async function matchApiEndpoints(
  documentId: number,
  integrationReqs: { id?: string; title?: string; description?: string }[],
  serviceId?: number,
  signal?: AbortSignal,
): Promise<ApiMatchItem[]> {
  return api.post(`/requirements/${documentId}/match-api`, {
    integration_reqs: integrationReqs,
    service_id: serviceId ?? null,
  }, { signal })
}

export async function fetchApiMatchSelection(
  documentId: number,
  signal?: AbortSignal,
): Promise<ApiMatchSelection> {
  return api.get(`/requirements/${documentId}/match-api/selection`, { signal })
}

export async function confirmApiMatches(
  documentId: number,
  selection: ApiMatchSelection,
): Promise<ApiMatchSelection> {
  return api.post(`/requirements/${documentId}/match-api/confirm`, selection)
}
