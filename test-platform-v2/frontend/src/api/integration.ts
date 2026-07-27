import api from './client'
import type { IntegrationConfig, SyncLog, TestConnectionResult } from '@/types'

const BASE = '/integrations'

export async function fetchIntegrations(): Promise<{ items: IntegrationConfig[]; total: number }> {
  return api.get(BASE)
}

export async function fetchIntegration(id: number): Promise<IntegrationConfig> {
  return api.get(`${BASE}/${id}`)
}

export async function createIntegration(body: {
  name: string
  provider_type: string
  base_url: string
  auth_json: string
  field_mapping?: string
  sync_direction?: string
  sync_interval_minutes?: number
  enabled?: boolean
}): Promise<IntegrationConfig> {
  return api.post(BASE, body)
}

export async function updateIntegration(id: number, body: Record<string, unknown>): Promise<IntegrationConfig> {
  return api.put(`${BASE}/${id}`, body)
}

export async function deleteIntegration(id: number): Promise<{ deleted: boolean }> {
  return api.delete(`${BASE}/${id}`)
}

export async function testConnection(body: {
  provider_type: string
  base_url: string
  auth_json: string
}): Promise<TestConnectionResult> {
  return api.post(`${BASE}/test-connection`, body)
}

export async function syncNow(id: number, direction?: string): Promise<{
  pushed: number; pulled: number; errors: number; message: string
}> {
  return api.post(`${BASE}/${id}/sync-now`, null, { params: direction ? { direction } : {} })
}

export async function fetchSyncLogs(id: number, params: { page?: number; page_size?: number } = {}): Promise<{
  items: SyncLog[]; total: number; page: number; page_size: number
}> {
  return api.get(`${BASE}/${id}/sync-logs`, { params })
}

export async function pushDefect(defectId: number, integrationId: number): Promise<SyncLog> {
  return api.post(`/defects/${defectId}/sync-push`, null, { params: { integration_id: integrationId } })
}

export async function pullDefect(defectId: number, integrationId: number): Promise<SyncLog> {
  return api.post(`/defects/${defectId}/sync-pull`, null, { params: { integration_id: integrationId } })
}
