import api, { cachedGet, clearApiCache } from './client'

export interface TestCaseFilter {
  case_id?: string
  domain?: string
  module?: string
  surface?: string
  taxonomy_domain?: string
  taxonomy_module?: string
  case_type?: string
  positive_negative?: string
  priority?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}

// ── Category types ──

export interface TestCaseModuleCategory {
  id?: number
  module: string
  count: number
}

export interface TestCaseDomainCategory {
  id?: number
  domain: string
  count: number
  modules: TestCaseModuleCategory[]
}

export interface TestCaseStats {
  total: number
  by_type: Record<string, number>
}

export interface TaxonomyModuleNode {
  name: string
  path: string
  count: number
  children: TaxonomyModuleNode[]
}

export interface TaxonomyDomainNode {
  domain: string
  count: number
  modules: TaxonomyModuleNode[]
}

export interface TaxonomySurfaceNode {
  surface: '用户端' | '运营后台' | '接口测试' | '其他'
  count: number
  domains: TaxonomyDomainNode[]
}

export async function fetchDomains(signal?: AbortSignal): Promise<TestCaseDomainCategory[]> {
  // Batch 176（FIX-173-P1-02）：传 signal 也命中会话缓存（域树静态数据跨页共享）
  return cachedGet<TestCaseDomainCategory[]>('/test-cases/domains', undefined, { ttl: 60_000, signal })
}

export async function fetchTestCaseStats(signal?: AbortSignal): Promise<TestCaseStats> {
  return cachedGet<TestCaseStats>('/test-cases/stats', undefined, { ttl: 60_000, signal })
}

export async function fetchTaxonomy(
  params: { case_type?: string; surface?: string } = {},
  signal?: AbortSignal,
): Promise<TaxonomySurfaceNode[]> {
  return cachedGet<TaxonomySurfaceNode[]>('/test-cases/taxonomy', params, { ttl: 60_000, signal })
}

// ── Category CRUD ──

export async function createDomain(name: string) {
  clearApiCache('/test-cases/domains')
  return api.post('/test-cases/domains', { name })
}

export async function deleteDomain(domainId: number) {
  clearApiCache('/test-cases/domains')
  return api.delete(`/test-cases/domains/${domainId}`)
}

export async function createModule(domainId: number, name: string) {
  clearApiCache('/test-cases/domains')
  return api.post(`/test-cases/domains/${domainId}/modules`, { name })
}

export async function deleteModule(domainId: number, moduleId: number) {
  clearApiCache('/test-cases/domains')
  return api.delete(`/test-cases/domains/${domainId}/modules/${moduleId}`)
}

export async function fetchTestCases(params: TestCaseFilter = {}, signal?: AbortSignal) {
  return api.get('/test-cases', { params, signal })
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

/** 带鉴权下载导入模板/当前筛选用例（batch-70）。 */
export async function downloadExport(
  format: 'excel' | 'xmind',
  params: Record<string, string> = {},
): Promise<Blob> {
  const { useAuthStore } = await import('@/stores/auth')
  const { token, currentProjectId } = useAuthStore.getState()
  const url = format === 'excel' ? exportExcelUrl(params) : exportXmindUrl(params)
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (currentProjectId) headers['X-Project-Id'] = String(currentProjectId)
  const resp = await fetch(url, { credentials: 'include', headers })
  if (!resp.ok) throw new Error('导出失败')
  return resp.blob()
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
