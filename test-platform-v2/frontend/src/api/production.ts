import { aitdeV2 } from './missions'

// ── AITDE V3.6 Production Evidence & Real-World Data Template domain types ──

/** A JSON-ish value that may arrive already parsed or as a raw string. */
export type JsonLike = Record<string, unknown> | string | null

export interface ObservationSession {
  id: number
  project_id: number
  mission_id?: number | null
  environment_id: number
  worker_id?: number | null
  mode: string
  status: string
  policy_version?: string | null
  started_by?: number | null
  started_at?: string | null
  finished_at?: string | null
}

export interface StartObservationSessionInput {
  project_id: number
  environment_id: number
  mission_id?: number | null
  worker_id?: number | null
  mode: string
  started_by?: number | null
  policy_version?: string | null
}

export interface Journey {
  id: number
  project_id: number
  session_id: number
  name: string
  journey_hash: string
  summary_json: JsonLike
  source_ref_json: JsonLike
  created_at?: string | null
}

export interface XhrRef {
  method?: string
  status?: number | string | null
  url?: string | null
  request_url?: string | null
  request_headers?: JsonLike
  request_body?: unknown
  response_headers?: JsonLike
  response_body?: unknown
  headers?: JsonLike
  body?: unknown
  [key: string]: unknown
}

export interface JourneyStep {
  sequence: number
  event_type: string
  semantic_action?: Record<string, unknown> | string | null
  url_template?: string | null
  xhr_refs?: XhrRef[] | Record<string, unknown> | string | null
  evidence_refs?: unknown[] | string | null
}

export interface JourneyDetail extends Journey {
  steps: JourneyStep[]
}

export interface InspectDataInput {
  project_id: number
  data_source_id: number
  sql: string
  schema_name?: string | null
  session_id?: number | null
  table_names?: string[]
}

export interface InspectDataResult {
  rows: unknown[]
  row_count: number
  duration_ms: number
}

export interface ExtractEntityGraphInput {
  project_id: number
  root_entity_type: string
  root_ref_hash: string
  source_environment_id: number
  mission_id?: number | null
}

export interface EntityNode {
  id: string
  label?: string | null
  entity_type?: string | null
  ref_hash?: string | null
  [key: string]: unknown
}

export interface EntityEdge {
  source: string
  target: string
  relation?: string | null
  [key: string]: unknown
}

export interface EntityGraphResult {
  id: number
  content_hash: string
  nodes: EntityNode[]
  edges: EntityEdge[]
}

export interface BuildTemplateInput {
  project_id: number
  name: string
  entity_graph_snapshot_id: number
  masking_profile_id?: number | null
  mission_id?: number | null
  created_by?: number | null
}

export interface BuildTemplateResult {
  id: number
  validation_status: string
}

export interface ValidateTemplateInput {
  project_id: number
  template_id: number
}

export interface ValidateTemplateResult {
  validation_status: string
  leaks: unknown[]
}

export interface MaterializeTemplateInput {
  project_id: number
  template_id: number
  target_environment_id: number
}

export interface MaterializeTemplateResult {
  materialization_id: number
}

export interface AnalyzeGapsInput {
  project_id: number
  journey_id: number
}

export interface GapCandidate {
  kind: string
  title: string
  confidence: number
  auto_approved: boolean
}

/** A masking rule that composes a masking profile (client-side DSL). */
export interface MaskingRule {
  id: string
  entity_pattern: string
  field_pattern: string
  classification: string
  strategy: 'REDACT' | 'HASH' | 'TOKENIZE' | 'FAKE' | 'PRESERVE'
  priority: number
}

/** A masking profile being composed in the masking UI. */
export interface MaskingProfile {
  id: string
  name: string
  description?: string | null
  rules: MaskingRule[]
}

// ── Observation sessions ──

export function startObservationSession(
  payload: StartObservationSessionInput,
): Promise<{ id: number }> {
  return aitdeV2.post('/production/observation-sessions', payload)
}

export function stopObservationSession(id: number): Promise<{ id: number }> {
  return aitdeV2.post(`/production/observation-sessions/${id}/stop`)
}

export function fetchObservationSession(id: number, signal?: AbortSignal): Promise<ObservationSession> {
  return aitdeV2.get(`/production/observation-sessions/${id}`, { signal })
}

// ── Journeys ──

export function fetchJourneys(sessionId?: number, signal?: AbortSignal): Promise<Journey[]> {
  return aitdeV2.get('/production/journeys', {
    params: sessionId != null ? { session_id: sessionId } : undefined,
    signal,
  })
}

export function fetchJourney(id: number, signal?: AbortSignal): Promise<JourneyDetail> {
  return aitdeV2.get(`/production/journeys/${id}`, { signal })
}

// ── Real-world data ──

export function inspectProductionData(payload: InspectDataInput): Promise<InspectDataResult> {
  return aitdeV2.post('/production/data/inspect', payload)
}

// ── Entity graphs (extract) ──

export function extractEntityGraph(payload: ExtractEntityGraphInput): Promise<EntityGraphResult> {
  return aitdeV2.post('/production/entity-graphs/extract', payload)
}

// ── Templates (build / validate / materialize) ──

export function buildTemplate(payload: BuildTemplateInput): Promise<BuildTemplateResult> {
  return aitdeV2.post('/production/templates', payload)
}

export function validateTemplate(
  id: number,
  payload: ValidateTemplateInput,
): Promise<ValidateTemplateResult> {
  return aitdeV2.post(`/production/templates/${id}/validate`, payload)
}

export function materializeTemplate(
  id: number,
  payload: MaterializeTemplateInput,
): Promise<MaterializeTemplateResult> {
  return aitdeV2.post(`/production/templates/${id}/materialize`, payload)
}

// ── Evidence gap analysis ──

export function analyzeGaps(journeyId: number, payload: AnalyzeGapsInput): Promise<GapCandidate[]> {
  return aitdeV2.post(`/production/evidence/${journeyId}/analyze-gaps`, payload)
}

// ── Label maps ──

export const SESSION_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '采集中', color: 'bg-status-info-muted text-status-info' },
  COMPLETED: { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  COMPLETE: { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  STOPPED: { label: '已停止', color: 'bg-status-warning-muted text-status-warning' },
  FAILED: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
}

export const OBSERVATION_MODE_LABELS: Record<string, { label: string; color: string }> = {
  OBSERVE: { label: '观察', color: 'bg-status-info-muted text-status-info' },
  REAL: { label: '真实流量', color: 'bg-status-warning-muted text-status-warning' },
  REPLAY: { label: '回放', color: 'bg-status-info-muted text-status-info' },
  STAGING: { label: '预发布', color: 'bg-status-warning-muted text-status-warning' },
  LIVE: { label: '线上', color: 'bg-status-danger-muted text-status-danger' },
}

export const TEMPLATE_VALIDATION_LABELS: Record<string, { label: string; color: string }> = {
  VALID: { label: 'Valid', color: 'bg-status-success-muted text-status-success' },
  OK: { label: 'Valid', color: 'bg-status-success-muted text-status-success' },
  INVALID: { label: 'Invalid', color: 'bg-status-danger-muted text-status-danger' },
  LEAKS_FOUND: { label: '发现泄漏', color: 'bg-status-danger-muted text-status-danger' },
  VALIDATING: { label: '校验中', color: 'bg-status-warning-muted text-status-warning' },
  DRAFT: { label: '草稿', color: 'bg-muted text-muted-foreground' },
}
