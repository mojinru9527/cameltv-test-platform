import api from './client'
import type { DefectItem, DefectTransition, DefectComment, DefectAttachment } from '@/types'

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

// ── Transitions ──

export async function fetchTransitions(defectId: number): Promise<DefectTransition[]> {
  const response = await api.get(`/defects/${defectId}/transitions`)
  return response as unknown as DefectTransition[]
}

export async function transitionDefect(defectId: number, data: { to_status: string; comment?: string }): Promise<DefectItem> {
  const response = await api.post(`/defects/${defectId}/transition`, data)
  return response as unknown as DefectItem
}

// ── Comments ──

export async function fetchComments(defectId: number): Promise<DefectComment[]> {
  const response = await api.get(`/defects/${defectId}/comments`)
  return response as unknown as DefectComment[]
}

export async function addComment(defectId: number, content: string): Promise<DefectComment> {
  const response = await api.post(`/defects/${defectId}/comments`, { content })
  return response as unknown as DefectComment
}

// ── Attachments ──

const BASE_URL = '/api/v1'

export async function fetchAttachments(defectId: number): Promise<DefectAttachment[]> {
  const response = await api.get(`/defects/${defectId}/attachments`)
  return response as unknown as DefectAttachment[]
}

export async function uploadAttachment(defectId: number, file: File): Promise<DefectAttachment> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post(`/defects/${defectId}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response as unknown as DefectAttachment
}

export function getAttachmentUrl(defectId: number, attachmentId: number): string {
  return `${BASE_URL}/defects/${defectId}/attachments/${attachmentId}`
}

export async function deleteAttachment(defectId: number, attachmentId: number): Promise<void> {
  await api.delete(`/defects/${defectId}/attachments/${attachmentId}`)
}
