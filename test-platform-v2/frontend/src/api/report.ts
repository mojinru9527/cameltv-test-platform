import api from './client'

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
