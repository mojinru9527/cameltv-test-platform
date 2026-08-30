import { aitdeV2 } from './missions'

// ── AITDE V3.5 Continuous Acceptance domain types ──

export interface Fingerprint {
  id: number
  environment_id: number
  fingerprint_hash: string
  build_label?: string | null
  components_json: Record<string, unknown> | string
  source_type: string
  captured_at: string | null
}

export interface BuildObservation {
  id: number
  mission_id: number
  environment_id: number
  fingerprint_id: number
  previous_fingerprint_id?: number | null
  change_summary_json: Record<string, unknown> | string
  detected_at: string | null
  status: string
}

export interface CampaignScenario {
  id: number
  campaign_id: number
  scenario_id: number
  scenario_version_id: number
  selection_reason_json: Record<string, unknown> | string
  required: string
  run_id?: number | null
}

export interface Campaign {
  id: number
  project_id: number
  mission_id: number
  name: string
  campaign_type: string
  environment_id: number
  build_observation_id?: number | null
  status: string
  created_by_type: string
  created_at: string | null
  scenarios?: CampaignScenario[]
}

export interface RunProfile {
  id: number
  project_id: number
  name: string
  selector_json: Record<string, unknown> | string
  evidence_policy_json: Record<string, unknown> | string
  retry_policy_json: Record<string, unknown> | string
  parallelism: number
  status: string
}

export interface Trigger {
  id: number
  project_id: number
  mission_id?: number | null
  trigger_type: string
  config_json: Record<string, unknown> | string
  status: string
  last_fired_at?: string | null
  created_at: string | null
}

export interface GateResult {
  id: number
  mission_id: number
  campaign_id?: number | null
  build_observation_id?: number | null
  policy_id: number
  result: string
  checks_json: Record<string, unknown> | string
  evaluated_at: string | null
  override_status?: string | null
  override_by?: number | null
  override_reason?: string | null
}

export interface BuildsResult {
  items: BuildObservation[]
}

export interface CampaignsResult {
  items: Campaign[]
}

export interface GateResultList {
  items: GateResult[]
}

export interface RunProfilesResult {
  items: RunProfile[]
}

export interface TriggersResult {
  items: Trigger[]
}

// ── Fingerprint / Builds ──

export function captureFingerprint(
  environmentId: number,
  payload: { build_label?: string; components?: Record<string, unknown>; source_type?: string },
): Promise<Fingerprint> {
  return aitdeV2.post(`/environments/${environmentId}/fingerprints/capture`, payload)
}

export function fetchMissionBuilds(missionId: number, signal?: AbortSignal): Promise<BuildsResult> {
  return aitdeV2.get(`/missions/${missionId}/builds`, { signal })
}

// ── Campaigns ──

export function createCampaign(payload: {
  project_id: number
  mission_id: number
  environment_id: number
  name?: string
  campaign_type?: string
  scenarios?: { scenario_id: number; scenario_version_id: number; required?: string; selection_reason?: Record<string, unknown> }[]
}): Promise<Campaign> {
  return aitdeV2.post('/campaigns', payload)
}

export function fetchCampaign(campaignId: number, signal?: AbortSignal): Promise<Campaign> {
  return aitdeV2.get(`/campaigns/${campaignId}`, { signal })
}

export function fetchMissionCampaigns(missionId: number, signal?: AbortSignal): Promise<CampaignsResult> {
  return aitdeV2.get(`/missions/${missionId}/campaigns`, { signal })
}

export function runCampaign(campaignId: number): Promise<Campaign> {
  return aitdeV2.post(`/campaigns/${campaignId}/run`)
}

// ── Acceptance / Gate ──

export function fetchMissionAcceptance(missionId: number, signal?: AbortSignal): Promise<GateResultList> {
  return aitdeV2.get(`/missions/${missionId}/acceptance`, { signal })
}

export function evaluateGate(
  missionId: number,
  payload: { project_id?: number; campaign_id?: number | null; build_observation_id?: number | null },
): Promise<GateResult> {
  return aitdeV2.post(`/missions/${missionId}/quality-gates/evaluate`, payload)
}

// ── Run Profiles / Triggers ──

export function fetchRunProfiles(signal?: AbortSignal): Promise<RunProfilesResult> {
  return aitdeV2.get('/run-profiles', { signal })
}

export function fetchTriggers(signal?: AbortSignal): Promise<TriggersResult> {
  return aitdeV2.get('/triggers', { signal })
}

// ── Label maps ──

export const GATE_RESULT_LABELS: Record<string, { label: string; color: string }> = {
  PASS: { label: 'PASS', color: 'bg-status-success-muted text-status-success' },
  FAIL: { label: 'FAIL', color: 'bg-status-danger-muted text-status-danger' },
  INCONCLUSIVE: { label: '无法判定', color: 'bg-status-warning-muted text-status-warning' },
}

export const BUILD_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  NEW: { label: '新Build', color: 'bg-status-info-muted text-status-info' },
  PLANNED: { label: '已规划', color: 'bg-status-info-muted text-status-info' },
  RUNNING: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  EVALUATED: { label: '已评估', color: 'bg-status-success-muted text-status-success' },
  IGNORED: { label: '已忽略', color: 'bg-muted text-muted-foreground' },
}
