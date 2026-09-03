import { aitdeV2 } from './missions'

export interface Ambiguity {
  id: number
  mission_id: number
  ambiguity_key: string
  title: string
  description: string
  severity: string
  status: string
  candidate_options_json: string
  selected_option_json: string
  ai_confidence: number
  resolution_note: string
  created_at: string | null
  updated_at: string | null
}

export interface Option {
  key: string
  label: string
}

export interface Intent {
  id: number
  mission_id: number
  intent_key: string
  title: string
  business_goal: string
  risk_level: string
  review_status: string
  created_at: string | null
  updated_at: string | null
}

export function analyzeMissionAmbiguities(
  missionId: number,
): Promise<{ ambiguity_count: number; intent_count: number }> {
  return aitdeV2.post(`/missions/${missionId}/ambiguities/analyze`)
}

export function fetchMissionAmbiguities(missionId: number, signal?: AbortSignal): Promise<Ambiguity[]> {
  return aitdeV2.get(`/missions/${missionId}/ambiguities`, { signal })
}

export function resolveAmbiguity(
  id: number,
  payload: { selected_option_key: string; resolution_note?: string; status?: string },
): Promise<Ambiguity> {
  return aitdeV2.post(`/ambiguities/${id}/resolve`, payload)
}

export function fetchMissionIntents(missionId: number): Promise<Intent[]> {
  return aitdeV2.get(`/missions/${missionId}/intents`)
}

export function reviewIntent(
  id: number,
  action: 'approve' | 'reject',
): Promise<Intent> {
  return aitdeV2.post(`/intents/${id}/review`, { action })
}

export const AMBIGUITY_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  OPEN: { label: '待解决', color: 'bg-status-warning-muted text-status-warning' },
  RESOLVED: { label: '已解决', color: 'bg-status-success-muted text-status-success' },
  DEFERRED: { label: '已延期', color: 'bg-muted text-muted-foreground' },
  OUT_OF_SCOPE: { label: '范围外', color: 'bg-muted text-muted-foreground' },
}
