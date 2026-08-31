import { aitdeV2 } from './missions'

// ── AITDE V3.1 Unified Execution domain types ──

export interface Adapter {
  id: number
  scenario_id: number
  scenario_version_id: number
  adapter_type: string
  status: string
  source_asset_type?: string | null
  source_asset_id?: string | null
  config_json: Record<string, unknown> | null
  adapter_version: string
  created_by: number
  created_at: string | null
  updated_at: string | null
}

export interface EnvironmentSnapshot {
  id: number
  environment_id: number
  mission_id: number
  build_label?: string | null
  frontend_version?: string | null
  service_versions_json: Record<string, unknown> | null
  openapi_hash?: string | null
  db_schema_version?: string | null
  config_hash?: string | null
  static_asset_hash?: string | null
  manual_note?: string | null
  fingerprint_hash: string
  captured_at: string | null
  created_by_type: string
}

export interface Run {
  id: number
  project_id: number
  mission_id: number
  scenario_id: number
  scenario_version_id: number
  contract_version_id: number
  adapter_id?: number | null
  environment_id: number
  environment_snapshot_id?: number | null
  runtime_status: string
  outcome?: string | null
  evidence_status: string
  trigger_type: string
  parent_run_id?: number | null
  retry_no: number
  started_at?: string | null
  finished_at?: string | null
  duration_ms?: number | null
  created_by: number
  created_at: string | null
}

export interface Step {
  id: number
  run_id: number
  sequence: number
  step_key: string
  step_type: string
  status: string
  error_type?: string | null
  error_message?: string | null
  input_snapshot_json?: Record<string, unknown> | null
  output_snapshot_json?: Record<string, unknown> | null
  trace_id?: string | null
  span_id?: string | null
  started_at?: string | null
  finished_at?: string | null
}

export interface Assertion {
  id: number
  run_id: number
  step_id?: number | null
  oracle_id: number
  oracle_snapshot_json: Record<string, unknown> | null
  expected_json: Record<string, unknown> | null
  actual_json: Record<string, unknown> | null
  result: string
  reason_code: string
  evidence_refs_json: Record<string, unknown> | null
  evaluated_at?: string | null
  /** V3.9 Trust — may be absent depending on API serialization. */ 
  oracle_source_type?: string | null
  /** V3.9 Trust — may be absent depending on API serialization. */ 
  trust_status?: string | null
}

export interface Evidence {
  id: number
  project_id: number
  run_id: number
  step_id?: number | null
  evidence_type: string
  storage_provider: string
  storage_uri: string
  content_hash: string
  content_type: string
  size_bytes: number
  sanitization_status: string
  sensitivity: string
  retention_class: string
  created_at: string | null
  /** V3.9 Trust — backends integrity status (VERIFIED/MISSING/CORRUPT/PENDING); may be absent. */
  integrity_status?: string | null
}

export interface MissionRunsParams {
  outcome?: string
  runtime_status?: string
  page?: number
  page_size?: number
}

export interface MissionRunsResult {
  total: number
  page: number
  page_size: number
  items: Run[]
}

export interface RunStepsResult {
  items: Step[]
}

export interface RunAssertionsResult {
  items: Assertion[]
}

export interface RunEvidenceResult {
  items: Evidence[]
}

export interface ScenarioAdaptersResult {
  items: Adapter[]
}

export interface RunReplayView {
  outcome: string | null
  runtime_status: string
  environment_snapshot_id: number | null
  timeline: Step[]
  assertions: Assertion[]
  evidence: Evidence[]
}

export interface RunReplay {
  manifest: Record<string, unknown>
  hash: string
  view: RunReplayView
}

// ── Input payloads ──

export interface CreateScenarioAdapterInput {
  scenario_version_id: number
  adapter_type: string
  source_asset_type?: string
  source_asset_id?: string
  config?: Record<string, unknown>
  adapter_version?: string
}

export interface UpdateAdapterInput {
  status?: string
  config?: Record<string, unknown>
  adapter_version?: string
}

export interface CaptureSnapshotInput {
  build_label?: string
  frontend_version?: string
  service_versions?: Record<string, unknown>
  openapi_hash?: string
  db_schema_version?: string
  config_hash?: string
  static_asset_hash?: string
  manual_note?: string
}

export interface CreateRunInput {
  mission_id: number
  scenario_version_id: number
  contract_version_id: number
  environment_id: number
  environment_snapshot_id?: number | null
  adapter_id?: number | null
  trigger_type?: string
}

// ── Adapters ──

export function fetchScenarioAdapters(
  scenarioId: number,
  signal?: AbortSignal,
): Promise<ScenarioAdaptersResult> {
  return aitdeV2.get(`/scenarios/${scenarioId}/adapters`, { signal })
}

export function createScenarioAdapter(
  scenarioId: number,
  payload: CreateScenarioAdapterInput,
): Promise<Adapter> {
  return aitdeV2.post(`/scenarios/${scenarioId}/adapters`, payload)
}

export function updateAdapter(adapterId: number, payload: UpdateAdapterInput): Promise<Adapter> {
  return aitdeV2.patch(`/scenarios/adapters/${adapterId}`, payload)
}

// ── Environment snapshot ──

export function captureSnapshot(
  environmentId: number,
  missionId: number,
  payload: CaptureSnapshotInput,
): Promise<EnvironmentSnapshot> {
  return aitdeV2.post(`/environments/${environmentId}/snapshots`, payload, {
    params: { mission_id: missionId },
  })
}

export function fetchLatestSnapshot(
  environmentId: number,
  missionId: number,
  signal?: AbortSignal,
): Promise<EnvironmentSnapshot | null> {
  return aitdeV2.get(`/environments/${environmentId}/snapshots/latest`, {
    params: { mission_id: missionId },
    signal,
  })
}

// ── Runs ──

export function createRun(scenarioId: number, payload: CreateRunInput): Promise<Run> {
  return aitdeV2.post(`/scenarios/${scenarioId}/runs`, payload)
}

export function fetchRun(runId: number, signal?: AbortSignal): Promise<Run> {
  return aitdeV2.get(`/runs/${runId}`, { signal })
}

/** Alias of fetchRun — a run's fetch endpoint is identical regardless of naming. */
export function fetchRuns(runId: number, signal?: AbortSignal): Promise<Run> {
  return fetchRun(runId, signal)
}

export function fetchMissionRuns(
  missionId: number,
  params: MissionRunsParams = {},
  signal?: AbortSignal,
): Promise<MissionRunsResult> {
  const query: Record<string, string | number> = {}
  if (params.outcome) query.outcome = params.outcome
  if (params.runtime_status) query.runtime_status = params.runtime_status
  if (params.page != null) query.page = params.page
  if (params.page_size != null) query.page_size = params.page_size
  return aitdeV2.get(`/missions/${missionId}/executions`, { params: query, signal })
}

export function cancelRun(runId: number): Promise<Run> {
  return aitdeV2.post(`/runs/${runId}/cancel`)
}

export function retryRun(runId: number): Promise<Run> {
  return aitdeV2.post(`/runs/${runId}/retry`)
}

export function finishRun(runId: number): Promise<Run> {
  return aitdeV2.post(`/runs/${runId}/finish`)
}

export function fetchRunSteps(runId: number, signal?: AbortSignal): Promise<RunStepsResult> {
  return aitdeV2.get(`/runs/${runId}/steps`, { signal })
}

export function fetchRunAssertions(
  runId: number,
  signal?: AbortSignal,
): Promise<RunAssertionsResult> {
  return aitdeV2.get(`/runs/${runId}/assertions`, { signal })
}

export function fetchRunEvidence(
  runId: number,
  signal?: AbortSignal,
): Promise<RunEvidenceResult> {
  return aitdeV2.get(`/runs/${runId}/evidence`, { signal })
}

export function fetchRunReplay(runId: number, signal?: AbortSignal): Promise<RunReplay> {
  return aitdeV2.get(`/runs/${runId}/replay`, { signal })
}

export interface AuditFeedback {
  id: number
  run_id: number
  audit_outcome: 'CONFIRMED' | 'FALSE_PASS' | 'FALSE_FAIL' | string
  reason: string
  created_by: number
  created_at: string | null
}

export interface SubmitAuditInput {
  audit_outcome: 'CONFIRMED' | 'FALSE_PASS' | 'FALSE_FAIL'
  reason?: string
}

export interface RunAuditResult {
  items: AuditFeedback[]
}

export function fetchRunAudit(runId: number, signal?: AbortSignal): Promise<RunAuditResult> {
  return aitdeV2.get(`/runs/${runId}/audit`, { signal })
}

export function submitRunAudit(runId: number, payload: SubmitAuditInput): Promise<AuditFeedback> {
  return aitdeV2.post(`/runs/${runId}/audit`, payload)
}

// ── UI label/colour maps ──

export const OUTCOME_LABELS: Record<string, { label: string; color: string }> = {
  PASS: { label: '通过', color: 'bg-status-success-muted text-status-success' },
  BUSINESS_FAIL: { label: '业务失败', color: 'bg-status-danger-muted text-status-danger' },
  AUTOMATION_FAIL: { label: '执行失败', color: 'bg-status-danger-muted text-status-danger' },
  DATA_FAIL: { label: '数据失败', color: 'bg-status-danger-muted text-status-danger' },
  ENV_FAIL: { label: '环境失败', color: 'bg-status-warning-muted text-status-warning' },
  ASSERTION_ERROR: { label: '断言错误', color: 'bg-status-warning-muted text-status-warning' },
  BLOCKED: { label: '已阻塞', color: 'bg-muted text-muted-foreground' },
  INCONCLUSIVE: { label: '无法判定', color: 'bg-status-warning-muted text-status-warning' },
}

export const RUNTIME_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  QUEUED: { label: '排队中', color: 'bg-status-info-muted text-status-info' },
  RUNNING: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  FINISHED: { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  CANCELLED: { label: '已取消', color: 'bg-muted text-muted-foreground' },
  // V3.4 Durable Runtime states — distinct from business failure.
  WAITING_WORKER: { label: '等待Worker', color: 'bg-status-warning-muted text-status-warning' },
  WAITING_APPROVAL: { label: '等待审批', color: 'bg-status-warning-muted text-status-warning' },
  RETRYING: { label: '重试中', color: 'bg-status-info-muted text-status-info' },
  RESUMING: { label: '恢复中', color: 'bg-status-info-muted text-status-info' },
}

export const AUDIT_OUTCOME_LABELS: Record<string, { label: string; color: string }> = {
  CONFIRMED: { label: '结论正确', color: 'bg-status-success-muted text-status-success' },
  FALSE_PASS: { label: '误报通过', color: 'bg-status-danger-muted text-status-danger' },
  FALSE_FAIL: { label: '误报失败', color: 'bg-status-warning-muted text-status-warning' },
}

export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  SCREENSHOT: '截图',
  VIDEO: '视频',
  NETWORK_LOG: '网络日志',
  CONSOLE_LOG: '控制台日志',
  API_RESPONSE: '接口响应',
  SYSTEM_LOG: '系统日志',
  TRACE: '链路',
}
