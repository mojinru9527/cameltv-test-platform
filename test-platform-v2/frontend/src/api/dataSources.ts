import { aitdeV2 } from './missions'
import { parseJson } from './json'

// ── AITDE V3.2 Data + DB Runtime: Data Source domain ──

export interface DataSource {
  id: number
  source_type: string
  name: string
  environment_id: number | null
  network_zone: string | null
  secret_ref: string | null
  access_mode: string
  /** Backend stores connection metadata as a JSON-encoded string; parsed here. */
  config_json: Record<string, unknown> | null
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

type RawDataSource = Omit<DataSource, 'config_json'> & {
  config_json?: string | null
}

function mapDataSource(raw: RawDataSource): DataSource {
  return {
    ...raw,
    config_json: parseJson(raw.config_json),
  }
}

export async function fetchDataSources(signal?: AbortSignal): Promise<DataSource[]> {
  const rows = (await aitdeV2.get('/data-sources', { signal })) as RawDataSource[]
  return (rows ?? []).map(mapDataSource)
}

export async function fetchDataSource(id: number, signal?: AbortSignal): Promise<DataSource> {
  const row = (await aitdeV2.get(`/data-sources/${id}`, { signal })) as RawDataSource
  return mapDataSource(row)
}

export async function createDataSource(payload: CreateDataSourceInput): Promise<DataSource> {
  const row = (await aitdeV2.post('/data-sources', payload)) as RawDataSource
  return mapDataSource(row)
}

export function testDataSourceConnection(id: number): Promise<DataSourceConnectionResult> {
  return aitdeV2.post(`/data-sources/${id}/test`)
}
