import client from './client'

export interface CoverageData {
  total_cases: number
  cases_in_plans: number
  cases_executed: number
  cases_passed: number
  cases_with_defects: number
  by_type: Record<string, number>
  by_domain: Record<string, number>
  coverage_rate: number
  execution_rate: number
  pass_rate: number
  requirement_count: number
  requirements_with_cases: number
}

export interface CaseTrace {
  case_id: string
  case_title: string
  domain: string
  module: string
  priority: string
  case_type: string
  plans: Array<{
    plan_id: number
    plan_name: string
    plan_status: string
    last_status: string
    executions: Array<{
      id: number
      status: string
      executed_at: string | null
      notes: string
    }>
  }>
  defects: Array<{
    defect_id: string
    title: string
    severity: string
    status: string
  }>
}

export async function fetchCoverage(): Promise<CoverageData> {
  return client.get('/trace/coverage') as Promise<CoverageData>
}

export async function fetchCaseTrace(caseId: number): Promise<CaseTrace> {
  return client.get(`/trace/case/${caseId}`) as Promise<CaseTrace>
}
