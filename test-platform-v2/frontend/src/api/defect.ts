import api from './client'

export interface DefectFilter {
  severity?: string
  status?: string
  assignee_id?: number
  keyword?: string
  page?: number
  page_size?: number
}

export async function fetchDefects(params: DefectFilter = {}) {
  return api.get('/defects', { params })
}

export async function fetchDefect(id: number) {
  return api.get(`/defects/${id}`)
}

export async function createDefect(body: Record<string, any>) {
  return api.post('/defects', body)
}

export async function updateDefect(id: number, body: Record<string, any>) {
  return api.put(`/defects/${id}`, body)
}

export async function deleteDefect(id: number) {
  return api.delete(`/defects/${id}`)
}

export async function fetchDefectStats() {
  return api.get('/defects/stats')
}
