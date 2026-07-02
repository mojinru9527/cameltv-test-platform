import api from './client'

// ── Types ──

export interface TrendPoint {
  date: string
  report_id: number
  pass_rate: number
  total: number
  pass: number
  fail: number
  skip: number
  block: number
  open_p0: number
  open_p1: number
  open_p2: number
  open_total: number
}

export interface TrendsData {
  points: TrendPoint[]
  summary: {
    total_reports: number
    avg_pass_rate: number
    best_pass_rate: number
    worst_pass_rate: number
    latest_open_defects: number
  }
}

// ── Report CRUD ──

export async function fetchReports(params: {
  keyword?: string
  page?: number
  page_size?: number
} = {}) {
  return api.get('/reports', { params })
}

export async function fetchReport(id: number) {
  return api.get(`/reports/${id}`)
}

export async function createReport(body: {
  plan_id: number
  name: string
  description?: string
}) {
  return api.post('/reports', body)
}

export async function deleteReport(id: number) {
  return api.delete(`/reports/${id}`)
}

// ── Report Export ──

export function exportReportUrl(id: number, format: 'csv' | 'excel' | 'pdf'): string {
  return `/api/v1/reports/${id}/export?format=${format}`
}

// ── Report Trends ──

export async function fetchTrends(): Promise<TrendsData> {
  const response = await api.get('/reports/trends')
  return response as unknown as TrendsData
}
