import api from './client'
import type { Dataset, DatasetListItem, DatasetPreview, DatasetUploadResponse } from '@/types'

const BASE = '/datasets'

export async function fetchDatasets(params: { page?: number; page_size?: number } = {}): Promise<{
  items: DatasetListItem[]; total: number; page: number; page_size: number
}> {
  return api.get(BASE, { params })
}

export async function fetchDataset(id: number): Promise<Dataset> {
  return api.get(`${BASE}/${id}`)
}

export async function createDataset(body: {
  name: string; description?: string; source_type: string; raw_content: string
}): Promise<DatasetUploadResponse> {
  return api.post(BASE, body)
}

export async function updateDataset(id: number, body: {
  name?: string; description?: string; raw_content?: string
}): Promise<Dataset> {
  return api.put(`${BASE}/${id}`, body)
}

export async function deleteDataset(id: number): Promise<{ deleted: number }> {
  return api.delete(`${BASE}/${id}`)
}

export async function uploadDatasetFile(
  file: File, name: string, description?: string
): Promise<DatasetUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('name', name)
  if (description) form.append('description', description)
  return api.post(`${BASE}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function previewDatasetRaw(
  raw_content: string, source_type: string
): Promise<DatasetPreview> {
  return api.post(`${BASE}/preview`, { raw_content, source_type })
}
