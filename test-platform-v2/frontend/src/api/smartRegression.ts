import { aitdeV2 } from './missions'

// ── AITDE V3.7 Impact Analysis + Smart Regression domain types ──

export interface ChangeItem {
  id: number
  change_set_id: number
  change_kind: string
  entity_type: string
  entity_key: string
  before: unknown | null
  after: unknown | null
  risk_hint: string
  source_refs: Record<string, unknown>[]
}

export interface ChangeSet {
  id: number
  project_id: number
  mission_id: number
  change_type: string
  source_from_ref?: string | null
  source_to_ref?: string | null
  status: string
  content_hash: string
  created_at: string | null
  items: ChangeItem[]
}

export interface ImpactResult {
  id: number
  impact_run_id: number
  scenario_id: number
  scenario_version_id: number
  impact_score: number
  risk_level: string
  reasons: string[]
  paths: string[][]
  decision: string
}

export interface ImpactRun {
  id: number
  project_id: number
  mission_id: number
  change_set_id: number
  algorithm_version: string
  status: string
  input_hash: string
  created_at: string | null
  finished_at: string | null
  results: ImpactResult[]
  unknown_changes: { entity_type: string; entity_key: string; risk_hint: string }[]
}

export interface SelectionItem {
  scenario_id: number
  scenario_version_id: number
  decision: string
  reason: string
}

export interface RegressionSelection {
  id: number
  mission_id: number
  impact_run_id?: number | null
  build_observation_id?: number | null
  selection_type: string
  selected: SelectionItem[]
  excluded: SelectionItem[]
  fallback_reason?: string | null
  content_hash: string
  created_at: string | null
}

export interface LineageEdge {
  id: number
  project_id: number
  mission_id?: number | null
  from: string
  from_type: string
  from_id: number
  to: string
  to_type: string
  to_id: number
  edge_type: string
  source_refs: Record<string, unknown>[]
  confidence: number
  created_by_type: string
  created_at: string | null
}

export interface GuardResult {
  ok: boolean
  selection_id: number
  fallback_to?: string | null
  fallback_reason?: string | null
  selected_count: number
  mission_scenario_count: number
}

export interface ExplainResult {
  scenario_id: number
  scenario_version_id?: number | null
  impact_score: number
  risk_level?: string | null
  reasons: string[]
  paths: string[][]
}

// ── ChangeSet detection ──

export function detectChanges(
  missionId: number,
  payload: {
    change_type: string
    baseline?: Record<string, unknown>
    current?: Record<string, unknown>
    source_from_ref?: string | null
    source_to_ref?: string | null
  },
): Promise<ChangeSet> {
  return aitdeV2.post(`/missions/${missionId}/changes/detect`, payload)
}

export function detectRisk(
  missionId: number,
  signals: { scenario_id: number; scenario_version_id?: number | null; risk_hint?: string; reason?: string; source_refs?: Record<string, unknown>[] }[],
): Promise<ChangeSet> {
  return aitdeV2.post(`/missions/${missionId}/changes/detect-risk`, { signals })
}

export function fetchChangeSet(changeSetId: number, signal?: AbortSignal): Promise<ChangeSet> {
  return aitdeV2.get(`/change-sets/${changeSetId}`, { signal })
}

// ── Impact analysis ──

export function analyzeImpact(changeSetId: number): Promise<ImpactRun> {
  return aitdeV2.post(`/change-sets/${changeSetId}/impact`)
}

export function fetchImpactRun(impactRunId: number, signal?: AbortSignal): Promise<ImpactRun> {
  return aitdeV2.get(`/impact-runs/${impactRunId}`, { signal })
}

export function explainImpact(impactRunId: number, scenarioId: number): Promise<ExplainResult> {
  return aitdeV2.get(`/impact-runs/${impactRunId}/scenarios/${scenarioId}/explanation`)
}

// ── Regression selection / guard / campaign ──

export function createSelection(
  impactRunId: number,
  payload: { selection_type?: string; build_observation_id?: number | null },
): Promise<RegressionSelection> {
  return aitdeV2.post(`/impact-runs/${impactRunId}/selections`, payload)
}

export function guardSelection(selectionId: number): Promise<GuardResult> {
  return aitdeV2.get(`/regression-selections/${selectionId}/guard`)
}

export function fetchRegressionSelection(selectionId: number, signal?: AbortSignal): Promise<RegressionSelection> {
  return aitdeV2.get(`/regression-selections/${selectionId}`, { signal })
}

export function createCampaignFromSelection(
  selectionId: number,
  payload: { name?: string; environment_id?: number },
): Promise<{ campaign_id: number; scenario_count: number; campaign_type: string; status: string }> {
  return aitdeV2.post(`/regression-selections/${selectionId}/campaign`, payload)
}

// ── Lineage ──

export function fetchLineage(missionId: number, signal?: AbortSignal): Promise<{ edges: LineageEdge[] }> {
  return aitdeV2.get(`/missions/${missionId}/lineage`, { signal })
}

export function backfillLineage(missionId: number): Promise<{ mission_id: number; created_edges: number; edge_count: number }> {
  return aitdeV2.post(`/missions/${missionId}/lineage/backfill`)
}

// ── Label maps ──

export const RISK_LABELS: Record<string, { label: string; color: string }> = {
  P0: { label: 'P0', color: 'bg-status-danger-muted text-status-danger' },
  P1: { label: 'P1', color: 'bg-status-warning-muted text-status-warning' },
  P2: { label: 'P2', color: 'bg-status-info-muted text-status-info' },
  P3: { label: 'P3', color: 'bg-muted text-muted-foreground' },
}

export const CHANGE_KIND_LABELS: Record<string, string> = {
  ADDED: '新增',
  CHANGED: '变更',
  DELETED: '删除',
}
