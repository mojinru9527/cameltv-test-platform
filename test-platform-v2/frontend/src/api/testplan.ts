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

export async function fetchPlan(id: number, signal?: AbortSignal) {
  if (signal) return api.get(`/test-plans/${id}`, { signal })
  return api.get(`/test-plans/${id}`)
}

// ── Execution ──

export async function fetchExecutions(planId: number, pcaseId?: number, signal?: AbortSignal) {
  return api.get(`/test-plans/${planId}/executions`, {
    params: { pcase_id: pcaseId || 0 },
    ...(signal ? { signal } : {}),
  })
}
