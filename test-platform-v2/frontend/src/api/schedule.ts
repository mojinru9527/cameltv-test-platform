import api from './client'

export async function fetchSchedules(params: {
  enabled?: boolean
  page?: number
  page_size?: number
} = {}) {
  return api.get('/schedules', { params })
}

export async function fetchSchedule(id: number) {
  return api.get(`/schedules/${id}`)
}

export async function createSchedule(body: {
  name: string
  description?: string
  plan_id: number
  cron_expression: string
  enabled?: boolean
}) {
  return api.post('/schedules', body)
}

export async function updateSchedule(id: number, body: Record<string, any>) {
  return api.put(`/schedules/${id}`, body)
}

export async function deleteSchedule(id: number) {
  return api.delete(`/schedules/${id}`)
}

export async function triggerSchedule(id: number) {
  return api.post(`/schedules/${id}/trigger`)
}

export async function fetchScheduleRuns(id: number, page: number = 1) {
  return api.get(`/schedules/${id}/runs`, { params: { page, page_size: 20 } })
}
