import api from './client'
import type {
  ApiExecutionResult, BatchExecutionResult,
  ApiService, ApiEndpoint, ApiImportPreview, ApiImportResult,
  ApiExecutionTask, ApiTaskDetail,
  GenerateApiCasesRequest, BatchGenerateRequest,
} from '@/types'
import type { ApiExecutionRequest } from '@/pages/apitest/apiExecutionRequest'

// ── 即时执行（保留原有） ──

/** 执行已保存的 API 用例 */
export async function executeApiCase(
  request: ApiExecutionRequest,
): Promise<ApiExecutionResult | BatchExecutionResult> {
  const caseId = request.case_ids[0]
  if (request.source !== 'single' || request.case_ids.length !== 1 || !caseId) {
    throw new Error('single execution requires exactly one case')
  }
  return api.post(`/test-cases/${caseId}/execute`, {
    ...request,
    request: null,
  })
}

/** 即时执行（不保存用例） */
export async function quickExecute(
  request: ApiExecutionRequest,
): Promise<ApiExecutionResult | BatchExecutionResult> {
  if ((request.source !== 'quick' && request.source !== 'asset') || !request.request) {
    throw new Error('quick and asset execution require a request definition')
  }
  return api.post('/apitest/api-execute', request)
}

// ── 服务管理 ──

export async function fetchApiServices(signal?: AbortSignal): Promise<ApiService[]> {
  if (signal) {
    return api.get('/apitest/services', { signal }) as unknown as Promise<ApiService[]>
  }
  return api.get('/apitest/services') as unknown as Promise<ApiService[]>
}

export async function createApiService(data: { name: string; display_name?: string; description?: string }): Promise<ApiService> {
  return api.post('/apitest/services', data) as unknown as Promise<ApiService>
}

// ── 接口资产管理 ──

export async function fetchApiEndpoints(params: {
  service_id?: number
  module?: string
  method?: string
  keyword?: string
  page?: number
  page_size?: number
}, signal?: AbortSignal): Promise<{ total: number; page: number; page_size: number; items: ApiEndpoint[] }> {
  return api.get('/apitest/endpoints', { params, ...(signal ? { signal } : {}) }) as unknown as Promise<{ total: number; page: number; page_size: number; items: ApiEndpoint[] }>
}

export async function createApiEndpoint(data: Partial<ApiEndpoint>): Promise<ApiEndpoint> {
  return api.post('/apitest/endpoints', data) as unknown as Promise<ApiEndpoint>
}

export async function updateApiEndpoint(endpointId: number, data: Partial<ApiEndpoint>): Promise<ApiEndpoint> {
  return api.put(`/apitest/endpoints/${endpointId}`, data) as unknown as Promise<ApiEndpoint>
}

// ── OpenAPI 导入 ──

export async function previewOpenApiImport(
  data: { service_name: string; source_type: string; source_ref?: string; spec_content?: string },
): Promise<ApiImportPreview> {
  return api.post('/apitest/import/preview', data) as unknown as Promise<ApiImportPreview>
}

export async function confirmOpenApiImport(
  data: { service_name: string; source_type: string; source_ref?: string; spec_content?: string; generate_cases?: boolean; create_plan?: boolean; plan_name?: string },
): Promise<ApiImportResult> {
  return api.post('/apitest/import/confirm', data) as unknown as Promise<ApiImportResult>
}

// ── 用例生成 ──

export async function generateApiCases(
  data: GenerateApiCasesRequest,
): Promise<{ cases: any[]; total: number; imported_case_ids: number[] }> {
  return api.post('/apitest/cases/generate', data) as unknown as Promise<{ cases: any[]; total: number; imported_case_ids: number[] }>
}

export async function batchGenerateApiCases(
  data: BatchGenerateRequest,
): Promise<{ total_generated: number; imported_case_ids: number[]; errors: any[] }> {
  return api.post('/apitest/cases/batch-generate', data) as unknown as Promise<{ total_generated: number; imported_case_ids: number[]; errors: any[] }>
}

// ── 批量执行任务 ──

export async function createApiExecutionTask(
  data: ApiExecutionRequest & { name: string; service_id?: number },
): Promise<ApiExecutionTask> {
  if (data.source !== 'group' && data.source !== 'batch') {
    throw new Error('task execution source must be group or batch')
  }
  return api.post('/apitest/tasks', data) as unknown as Promise<ApiExecutionTask>
}

export async function fetchApiExecutionTasks(params: {
  service_id?: number
  status?: string
  page?: number
  page_size?: number
}): Promise<{ total: number; page: number; page_size: number; items: ApiExecutionTask[] }> {
  return api.get('/apitest/tasks', { params }) as unknown as Promise<{ total: number; page: number; page_size: number; items: ApiExecutionTask[] }>
}

export async function fetchApiExecutionTask(taskId: number): Promise<ApiTaskDetail> {
  return api.get(`/apitest/tasks/${taskId}`) as unknown as Promise<ApiTaskDetail>
}

export async function cancelApiExecutionTask(taskId: number): Promise<{ status: string }> {
  return api.post(`/apitest/tasks/${taskId}/cancel`) as unknown as Promise<{ status: string }>
}
