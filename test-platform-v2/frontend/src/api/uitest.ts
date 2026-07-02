import api from './client'

export async function fetchUiJobs(params: Record<string, any> = {}) {
  return api.get('/ui-tests', { params })
}

export async function fetchUiJob(id: number) {
  return api.get(`/ui-tests/${id}`)
}

export async function createUiJob(body: Record<string, any>) {
  return api.post('/ui-tests', body)
}

export async function updateUiJob(id: number, body: Record<string, any>) {
  return api.put(`/ui-tests/${id}`, body)
}

export async function deleteUiJob(id: number) {
  return api.delete(`/ui-tests/${id}`)
}

export async function triggerUiJob(id: number) {
  return api.post(`/ui-tests/${id}/trigger`)
}

export async function fetchUiRuns(jobId: number, params: Record<string, any> = {}) {
  return api.get(`/ui-tests/${jobId}/runs`, { params })
}

export async function fetchScripts(): Promise<string[]> {
  return api.get('/ui-tests/scripts')
}
