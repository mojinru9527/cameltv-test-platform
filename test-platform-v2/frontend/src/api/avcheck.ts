import api from './client'
import type { AvMeasurementItem, AvMeasurementTemplate, AvTaskItem } from '@/types'

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

export async function updateAvTask(id: number, body: Record<string, any>): Promise<AvTaskItem> {
  return api.put(`/av-checks/${id}`, body)
}

export async function fetchAvMeasurementTemplates(): Promise<AvMeasurementTemplate[]> {
  return api.get('/av-checks/templates/measurements')
}

export interface AvMeasurementPayload {
  metric_type: string
  scenario: string
  method: string
  environment: string
  device_info: string
  network_condition: string
  samples: number[]
  threshold?: number
  notes: string
}

export async function createAvMeasurement(
  taskId: number,
  body: AvMeasurementPayload,
): Promise<AvMeasurementItem> {
  return api.post(`/av-checks/${taskId}/measurements`, body)
}

export async function updateAvMeasurement(
  taskId: number,
  measurementId: number,
  body: AvMeasurementPayload,
): Promise<AvMeasurementItem> {
  return api.put(`/av-checks/${taskId}/measurements/${measurementId}`, body)
}

export async function deleteAvMeasurement(taskId: number, measurementId: number) {
  return api.delete(`/av-checks/${taskId}/measurements/${measurementId}`)
}
