import api from './client'

export interface TestCaseDomainCategory {
  id?: number
  domain: string
  count: number
  modules: TestCaseModuleCategory[]
}

export interface TestCaseModuleCategory {
  id?: number
  module: string
  count: number
}

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

// ── Excel import/export ──

export function exportExcelUrl(params: Record<string, string> = {}): string {
  const qs = new URLSearchParams(params).toString()
  return `${api.defaults.baseURL}/test-cases/export/excel${qs ? `?${qs}` : ''}`
}

export async function importExcel(file: File): Promise<{ imported: number; total: number }> {
  const form = new FormData()
  form.append('file', file)
  return api.post('/test-cases/import/excel', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function exportXmindUrl(params: Record<string, string> = {}): string {
  const qs = new URLSearchParams(params).toString()
  return `${api.defaults.baseURL}/test-cases/export/xmind${qs ? `?${qs}` : ''}`
}

export async function importXmind(file: File): Promise<{ imported: number; total: number }> {
  const form = new FormData()
  form.append('file', file)
  return api.post('/test-cases/import/xmind', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── Version history ──

export async function fetchVersions(caseId: number): Promise<import('@/types').TestCaseVersion[]> {
  return api.get(`/test-cases/${caseId}/versions`)
}

export async function fetchVersionDetail(caseId: number, versionId: number): Promise<import('@/types').TestCaseVersionDetail> {
  return api.get(`/test-cases/${caseId}/versions/${versionId}`)
}

// ── Review ──

export async function reviewCase(caseId: number, action: string, comment: string = ''): Promise<any> {
  return api.post(`/test-cases/${caseId}/review`, { action, comment })
}

export async function fetchReviewHistory(caseId: number): Promise<import('@/types').TestCaseReviewTransition[]> {
  return api.get(`/test-cases/${caseId}/review-history`)
}

// ── Category management ──

export async function createDomain(name: string): Promise<any> {
  return api.post('/test-cases/domains', { name })
}

export async function updateDomain(id: number, name: string): Promise<any> {
  return api.put(`/test-cases/domains/${id}`, { name })
}

export async function deleteDomain(id: number): Promise<any> {
  return api.delete(`/test-cases/domains/${id}`)
}

export async function createModule(domainId: number, name: string): Promise<any> {
  return api.post('/test-cases/modules', { domain_id: domainId, name })
}

export async function updateModule(id: number, name: string): Promise<any> {
  return api.put(`/test-cases/modules/${id}`, { name })
}

export async function deleteModule(id: number): Promise<any> {
  return api.delete(`/test-cases/modules/${id}`)
}
