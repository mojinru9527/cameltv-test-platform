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

// ── Triage ──

export interface TriageClassified {
  execution_id: number
  case_id: number
  case_title: string
  case_type: string
  priority: string
  category: 'bug' | 'flaky_env' | 'case_defect' | 'known_issue'
  confidence: number
  explanation: string
  suggested_action: string
  notes: string
  result_data: Record<string, any>
  executed_at: string
}

export interface TriageResult {
  plan_id: number
  total_failures: number
  classified: TriageClassified[]
  summary: Record<string, number>
  analysis_method: 'llm' | 'rule_only'
}

export async function triagePlanFailures(planId: number): Promise<TriageResult> {
  return api.post(`/test-plans/${planId}/triage`)
}

export interface TriageDefectDraft {
  title: string
  description: string
  severity: string
  priority: string
  execution_id: number
}

export async function triageDraftDefect(planId: number, executionId: number): Promise<TriageDefectDraft> {
  return api.post(`/test-plans/${planId}/triage/${executionId}/draft-defect`)
}

// ── Execution ──

export async function executeCase(planId: number, pcaseId: number, body: { status: string; actual_result?: string; notes?: string }) {
  return api.post(`/test-plans/${planId}/cases/${pcaseId}/execute`, body)
}

export async function fetchExecutions(planId: number, pcaseId?: number) {
  return api.get(`/test-plans/${planId}/executions`, { params: { pcase_id: pcaseId || 0 } })
}

export async function autoExecutePlan(planId: number) {
  return api.post(`/test-plans/${planId}/auto-execute`)
}
