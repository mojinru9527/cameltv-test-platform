import { aitdeV2 } from './missions'

// ── AITDE V3.2 Data + DB Runtime: Data Source domain ──

export interface DataSource {
  id: number
  source_type: string
  name: string
  environment_id: number | null
  network_zone: string | null
  secret_ref: string | null
  access_mode: string
  config: Record<string, unknown> | null
  policy_ref: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DataSourceConnectionResult {
  ok: boolean
  latency_ms: number | null
  detail: string | null
  secret_leaked: boolean
  data_source_id: number
  source_type: string
  access_mode: string
}

export interface CreateDataSourceInput {
  source_type: string
  name: string
  environment_id?: number | null
  network_zone?: string | null
  secret_ref?: string | null
  access_mode?: string
  config?: Record<string, unknown> | null
  policy_ref?: string | null
}

export function fetchDataSources(signal?: AbortSignal): Promise<DataSource[]> {
  return aitdeV2.get('/data-sources', { signal })
}

export function fetchDataSource(id: number, signal?: AbortSignal): Promise<DataSource> {
  return aitdeV2.get(`/data-sources/${id}`, { signal })
}

export function createDataSource(payload: CreateDataSourceInput): Promise<DataSource> {
  return aitdeV2.post('/data-sources', payload)
}

export function testDataSourceConnection(id: number): Promise<DataSourceConnectionResult> {
  return aitdeV2.post(`/data-sources/${id}/test`)
}
