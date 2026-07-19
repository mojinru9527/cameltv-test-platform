import api from './client'

// ── Device ──

export interface PerfDevice {
  device_id: string
  device_name: string
  device_model: string
  platform: string  // "Android" | "iOS"
  os_version: string
  status: string     // "online" | "offline"
  installed_apps?: string[]
}

export async function fetchDevices(): Promise<PerfDevice[]> {
  const res: any = await api.get('/perf-sessions/devices')
  return res.devices ?? []
}

// ── Session ──

export interface PerfSession {
  id: number
  session_id: string
  device_id: string
  device_name: string
  device_model: string
  platform: string
  pkg_name: string
  metrics: string        // comma-separated
  status: string         // "pending" | "running" | "completed" | "failed" | "cancelled"
  duration: number
  actual_duration_s: number
  summary_json: string
  error_message: string
  creator_id: number
  created_at: string
  started_at: string | null
  ended_at: string | null
}

export interface PerfSessionCreate {
  device_id: string
  platform: string
  pkg_name: string
  device_name?: string
  device_model?: string
  metrics: string[]
  duration: number
}

export async function fetchSessions(params: Record<string, any> = {}): Promise<{
  items: PerfSession[]
  total: number
  page: number
  page_size: number
}> {
  return api.get('/perf-sessions', { params }) as any
}

export async function fetchSession(id: number): Promise<PerfSession> {
  return api.get(`/perf-sessions/${id}`)
}

export async function createSession(body: PerfSessionCreate): Promise<PerfSession> {
  return api.post('/perf-sessions', body)
}

export async function deleteSession(id: number): Promise<void> {
  return api.delete(`/perf-sessions/${id}`)
}

export async function startSession(id: number): Promise<{ status: string; started_at: string }> {
  return api.post(`/perf-sessions/${id}/start`)
}

export async function stopSession(id: number): Promise<{ status: string; duration_s: number }> {
  return api.post(`/perf-sessions/${id}/stop`)
}

// ── Metrics ──

export interface MetricDataPoint {
  timestamp: number
  elapsed_s: number
  values: Record<string, any>
}

export async function fetchMetrics(
  sessionId: number,
  sinceTs: number = 0,
): Promise<{ session_id: string; metrics: MetricDataPoint[] }> {
  return api.get(`/perf-sessions/${sessionId}/metrics`, {
    params: { sinceTs },
  }) as any
}

// ── Report ──

export interface MetricStatsItem {
  metric_type: string
  unit: string
  samples: number
  mean: number
  median: number
  p95: number
  min_val: number
  max_val: number
  stddev: number
  threshold: number
  threshold_comparator: string
  passed: boolean
}

export interface Anomaly {
  timestamp: number
  event_type: string
  detail: string
  metric_snapshot?: Record<string, any>
}

export interface PerfReport {
  session: PerfSession
  metrics: MetricStatsItem[]
  anomalies: Anomaly[]
}

export async function fetchReport(sessionId: number): Promise<PerfReport> {
  return api.get(`/perf-sessions/${sessionId}/report`)
}

// ── Compare ──

export interface MetricDelta {
  metric_type: string
  session_a_mean: number
  session_b_mean: number
  delta_absolute: number
  delta_percent: number
  direction: string
  significant: boolean
}

export interface CompareResponse {
  session_a: PerfSession
  session_b: PerfSession
  deltas: MetricDelta[]
}

export async function compareSessions(aId: number, bId: number): Promise<CompareResponse> {
  return api.post('/perf-sessions/compare', { session_a_id: aId, session_b_id: bId })
}
