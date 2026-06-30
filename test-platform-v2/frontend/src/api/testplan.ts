import api from './client'

// ── Plan ──

export interface PlanFilter {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}

export async function fetchPlans(params: PlanFilter = {}) {
  return api.get('/test-plans', { params })
}

export async function fetchPlan(id: number) {
  return api.get(`/test-plans/${id}`)
}

export async function createPlan(body: Record<string, any>) {
  return api.post('/test-plans', body)
}

export async function updatePlan(id: number, body: Record<string, any>) {
  return api.put(`/test-plans/${id}`, body)
}

export async function deletePlan(id: number) {
  return api.delete(`/test-plans/${id}`)
}

// ── Cases ──

export async function addCasesToPlan(planId: number, caseIds: number[]) {
  return api.post(`/test-plans/${planId}/cases`, { case_ids: caseIds })
}

export async function removeCasesFromPlan(planId: number, caseIds: number[]) {
  return api.delete(`/test-plans/${planId}/cases`, { data: { case_ids: caseIds } })
}

// ── Execution ──

export async function executeCase(planId: number, pcaseId: number, body: { status: string; actual_result?: string; notes?: string }) {
  return api.post(`/test-plans/${planId}/cases/${pcaseId}/execute`, body)
}

export async function fetchExecutions(planId: number, pcaseId?: number) {
  return api.get(`/test-plans/${planId}/executions`, { params: { pcase_id: pcaseId || 0 } })
}
