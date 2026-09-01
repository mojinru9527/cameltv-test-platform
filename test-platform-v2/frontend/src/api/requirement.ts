import api from './client'
import type {
  AIGenerateResult,
  ApiMatchItem,
  ApiMatchSelection,
  ExtractionQuality,
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

export async function extractFeaturesAsync(
  documentId: number,
): Promise<{ id: string; status: string }> {
  return api.post(`/requirements/${documentId}/extract-async`)
}

export async function generateTestCasesAsync(
  documentId: number,
  options?: Record<string, unknown>,
): Promise<{ id: string; status: string }> {
  return api.post(`/requirements/${documentId}/generate-async`, options || {})
}

export async function fetchAiTask(
  taskId: string,
): Promise<{ id: string; status: string; result?: unknown; error?: string }> {
  return api.get(`/requirements/ai-task/${taskId}`)
}

export async function runAsyncAiTask(
  taskId: string,
  signal?: AbortSignal,
): Promise<any> {
  // C102-1/C116-2：轮询异步 AI 任务（2s/次），完成返回 result，失败抛错。
  for (let i = 0; i < 300; i += 1) {
    if (signal?.aborted) throw new Error('已取消')
    const task = await fetchAiTask(taskId)
    if (task.status === 'done') return task.result
    if (task.status === 'failed') throw new Error(task.error || 'AI 任务失败')
    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
  throw new Error('AI 任务超时')
}

export async function getExtraction(
  documentId: number,
  signal?: AbortSignal,
): Promise<FeatureExtractionResult | null> {
  // 「首次尚无拆分结果」是预期路径，不应弹全局错误 toast。
  // 生产曾把 envelope 的 msg「功能拆分结果」当作错误直接弹给用户（P1-3）。
  return api.get(`/requirements/${documentId}/extraction`, {
    signal,
    suppressErrorToast: true,
  })
}

/**
 * 读取 envelope 业务错误码。
 *
 * P1-3 缺陷根因：原实现写作
 *   `(error as { code?: number }).code ?? error.response?.data?.code`
 * 而 axios 错误对象**恒带**字符串 `code`（如 `'ERR_BAD_REQUEST'`），`??` 因此
 * 提前短路，永远读不到 envelope 的 404 —— 降级到 `extractFeatures` 的分支从未
 * 生效，「功能拆分」按钮在后端返回 HTTP 404 时完全失效。
 *
 * 这里只接受**数值型**业务码，并同时兼容两种后端形态：
 *   - HTTP 200 + envelope code=404（拦截器抛出的 businessError.code）
 *   - HTTP 404 + body {"code":404}（axios error.response.data.code）
 *   - 兜底取 HTTP status，避免后端未带 envelope 时再次失效
 */
export function readEnvelopeCode(error: unknown): number | undefined {
  if (typeof error !== 'object' || error === null) return undefined

  const direct = (error as { code?: unknown }).code
  if (typeof direct === 'number') return direct

  const fromBody = (error as { response?: { data?: { code?: unknown } } }).response?.data?.code
  if (typeof fromBody === 'number') return fromBody

  const status = (error as { response?: { status?: unknown } }).response?.status
  return typeof status === 'number' ? status : undefined
}

export async function getOrCreateExtraction(
  documentId: number,
  signal?: AbortSignal,
): Promise<FeatureExtractionResult> {
  try {
    const existing = await getExtraction(documentId, signal)
    return existing === null ? extractFeatures(documentId, signal) : existing
  } catch (error) {
    if (readEnvelopeCode(error) === 404) {
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

export interface ImportCasesResult {
  imported: number
  skipped: number
  total: number
  plan_id: number | null
  plan_name: string
}

export async function importCases(
  documentId: number,
  indices: number[],
  editedCases?: AIGeneratedCase[],
  createPlan: boolean = false,
  createUiCases: boolean = false,
): Promise<ImportCasesResult> {
  return api.post(`/requirements/${documentId}/import`, {
    indices,
    ...(editedCases && editedCases.length > 0 ? { edited_cases: editedCases } : {}),
    create_plan: createPlan,
    create_ui_cases: createUiCases,
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


// ── Batch 119 / C102-4 前端差异面板 ──

export async function listReleaseBundles(signal?: AbortSignal): Promise<{ items: Array<{ id: number; name: string; client_version: string; status: string }>; total: number }> {
  return api.get('/release-bundles', { params: { page: 1, page_size: 100 }, signal })
}

export async function interactionCoverageGaps(
  edges: Array<{ from_module: string; entry?: string; to: string; from?: string }>,
  signal?: AbortSignal,
): Promise<{
  total_edges: number
  covered_edges: number
  gap_edges: number
  coverage_rate: number
  gaps: Array<{ from_module: string; entry: string; to: string }>
}> {
  return api.post('/interaction-coverage/gaps', { edges }, { signal })
}

export async function getCaptureTask(
  taskId: string,
): Promise<{ task_id: string; status: string; pages?: string[]; samples?: unknown[] }> {
  return api.get(`/ui-tests/capture/${taskId}`)
}

export async function productionDiff(
  releaseBundleId: number,
  productionPages: Array<{ label: string; title?: string; url?: string }>,
): Promise<{
  summary: { production_total: number; requirement_total: number; new_count: number; matched_count: number; missing_count: number }
  items: Array<{ name: string; change_type: 'new' | 'matched' | 'missing'; matched_with?: string; source?: string }>
  warnings: string[]
}> {
  return api.post('/requirement-modules/production-diff', {
    release_bundle_id: releaseBundleId,
    production_pages: productionPages,
  })
}



// ── Batch 167: 提取质量 + 按已导入接口生成接口用例 ──

export async function fetchExtractionQuality(
  documentId: number,
  signal?: AbortSignal,
): Promise<ExtractionQuality> {
  return api.get(`/requirements/${documentId}/extraction-quality`, { signal })
}

export async function generateApiFromEndpoints(
  documentId: number,
  serviceId?: number,
): Promise<{ matched: number; generated: number; upserted: number; endpoints: unknown[]; message: string }> {
  return api.post(`/requirements/${documentId}/generate-api-from-endpoints`, null, {
    params: serviceId ? { service_id: serviceId } : {},
  })
}

