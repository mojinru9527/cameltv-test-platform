import api from './client'

export interface TestCaseFilter {
  domain?: string
  module?: string
  case_type?: string
  priority?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}

export async function fetchDomains() {
  return api.get('/test-cases/domains')
}

export async function fetchTestCases(params: TestCaseFilter = {}) {
  return api.get('/test-cases', { params })
}

export async function fetchTestCase(id: number) {
  return api.get(`/test-cases/${id}`)
}

export async function createTestCase(body: Record<string, any>) {
  return api.post('/test-cases', body)
}

export async function updateTestCase(id: number, body: Record<string, any>) {
  return api.put(`/test-cases/${id}`, body)
}

export async function deleteTestCase(id: number) {
  return api.delete(`/test-cases/${id}`)
}

export async function batchUpdateCases(ids: number[], fields: Record<string, any>) {
  return api.put('/test-cases/batch', { ids, ...fields })
}

export async function batchDeleteCases(ids: number[]) {
  return api.delete('/test-cases/batch', { data: { ids } })
}
