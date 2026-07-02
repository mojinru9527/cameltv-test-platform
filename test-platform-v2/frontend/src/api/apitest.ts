import api from './client'
import type { ApiExecutionResult, BatchExecutionResult } from '@/types'

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
