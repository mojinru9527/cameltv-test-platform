import api from './client'

export async function fetchAvTasks(params: Record<string, any> = {}) {
  return api.get('/av-checks', { params })
}

export async function fetchAvTask(id: number) {
  return api.get(`/av-checks/${id}`)
}

export async function createAvTask(body: Record<string, any>) {
  return api.post('/av-checks', body)
}

export async function deleteAvTask(id: number) {
  return api.delete(`/av-checks/${id}`)
}

export async function triggerAvCheck(id: number) {
  return api.post(`/av-checks/${id}/trigger`)
}

export async function fetchAvMetrics(taskId: number) {
  return api.get(`/av-checks/${taskId}/metrics`)
}
