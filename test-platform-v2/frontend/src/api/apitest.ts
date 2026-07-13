import api from './client'
import type {
  ApiExecutionResult, BatchExecutionResult,
  ApiService, ApiEndpoint, ApiImportPreview, ApiImportResult,
  ApiExecutionTask, ApiTaskDetail,
  GenerateApiCasesRequest, BatchGenerateRequest, ApiTaskCreateRequest,
} from '@/types'

// ── 即时执行（保留原有） ──

/** 执行已保存的 API 用例 */
export async function executeApiCase(
  caseId: number,
  environmentId?: number,
  datasetId?: number,
): Promise<ApiExecutionResult | BatchExecutionResult> {
  return api.post(`/test-cases/${caseId}/execute`, {
    environment_id: environmentId ?? null,
    dataset_id: datasetId ?? null,
  })
}

/** 即时执行（不保存用例） */
export async function quickExecute(request: {
  method: string
  url: string
  headers?: string
  body?: string
  assertions?: string
  environment_id?: number
  dataset_id?: number
  service_name?: string
  query_params?: string
}): Promise<ApiExecutionResult | BatchExecutionResult> {
  return api.post('/apitest/api-execute', {
    method: request.method,
    url: request.url,
    headers: request.headers || '{}',
    body: request.body || '',
    assertions: request.assertions || '[]',
    environment_id: request.environment_id ?? null,
    dataset_id: request.dataset_id ?? null,
  })
}

// ── 服务管理 ──

export async function fetchApiServices(): Promise<ApiService[]> {
  return api.get('/apitest/services').then(r => r.data)
}

export async function createApiService(data: { name: string; display_name?: string; description?: string }): Promise<ApiService> {
  return api.post('/apitest/services', data).then(r => r.data)
}

// ── 接口资产管理 ──

export async function fetchApiEndpoints(params: {
  service_id?: number
  module?: string
  method?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<{ total: number; page: number; page_size: number; items: ApiEndpoint[] }> {
  return api.get('/apitest/endpoints', { params }).then(r => r.data)
}

export async function createApiEndpoint(data: Partial<ApiEndpoint>): Promise<ApiEndpoint> {
  return api.post('/apitest/endpoints', data).then(r => r.data)
}

export async function updateApiEndpoint(endpointId: number, data: Partial<ApiEndpoint>): Promise<ApiEndpoint> {
  return api.put(`/apitest/endpoints/${endpointId}`, data).then(r => r.data)
}

// ── OpenAPI 导入 ──

export async function previewOpenApiImport(
  data: { service_name: string; source_type: string; source_ref?: string; spec_content?: string },
): Promise<ApiImportPreview> {
  return api.post('/apitest/import/preview', data).then(r => r.data)
}

export async function confirmOpenApiImport(
  data: { service_name: string; source_type: string; source_ref?: string; spec_content?: string; generate_cases?: boolean },
): Promise<ApiImportResult> {
  return api.post('/apitest/import/confirm', data).then(r => r.data)
}

// ── 用例生成 ──

export async function generateApiCases(
  data: GenerateApiCasesRequest,
): Promise<{ cases: any[]; total: number; imported_case_ids: number[] }> {
  return api.post('/apitest/cases/generate', data).then(r => r.data)
}

export async function batchGenerateApiCases(
  data: BatchGenerateRequest,
): Promise<{ total_generated: number; imported_case_ids: number[]; errors: any[] }> {
  return api.post('/apitest/cases/batch-generate', data).then(r => r.data)
}

// ── 批量执行任务 ──

export async function createApiExecutionTask(
  data: ApiTaskCreateRequest,
): Promise<ApiExecutionTask> {
  return api.post('/apitest/tasks', data).then(r => r.data)
}

export async function fetchApiExecutionTasks(params: {
  service_id?: number
  status?: string
  page?: number
  page_size?: number
}): Promise<{ total: number; page: number; page_size: number; items: ApiExecutionTask[] }> {
  return api.get('/apitest/tasks', { params }).then(r => r.data)
}

export async function fetchApiExecutionTask(taskId: number): Promise<ApiTaskDetail> {
  return api.get(`/apitest/tasks/${taskId}`).then(r => r.data)
}

export async function cancelApiExecutionTask(taskId: number): Promise<{ status: string }> {
  return api.post(`/apitest/tasks/${taskId}/cancel`).then(r => r.data)
}
