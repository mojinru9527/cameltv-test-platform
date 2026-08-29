import { aitdeV2 } from './missions'
import { parseJson } from './json'
import type { CommandIR } from './actionPlans'

// ── AITDE V3.3 Browser + Hybrid + Assisted Manual: runtime interaction domain ──
// Covers browser sessions (Observe), manual-assist steps, and hybrid runs.

export type BrowserSessionMode = 'OBSERVE' | 'EXPLORE' | 'REGRESSION' | 'MANUAL_ASSIST'

export interface BrowserSession {
  id: string
  mission_id: number
  environment_id: number | null
  mode: BrowserSessionMode | string
  status: string
  browser_type: string | null
  context_ref: string | null
}

export interface StartBrowserSessionInput {
  mission_id: number
  environment_id: number
  mode: BrowserSessionMode | string
  browser_type?: string
  context_ref?: string
}

export interface BrowserSessionEvent {
  id: string
  sequence: number
  event_type: string
  /** Server-side redacted semantic target, stored as JSON string; parsed here. */
  semantic_target_json: Record<string, unknown> | null
  payload_ref_json: Record<string, unknown> | null
}

type RawBrowserSessionEvent = Omit<BrowserSessionEvent, 'semantic_target_json' | 'payload_ref_json'> & {
  semantic_target_json?: string | null
  payload_ref_json?: string | null
}

function mapEvent(raw: RawBrowserSessionEvent): BrowserSessionEvent {
  return {
    ...raw,
    semantic_target_json: parseJson(raw.semantic_target_json),
    payload_ref_json: parseJson(raw.payload_ref_json),
  }
}

export function startBrowserSession(payload: StartBrowserSessionInput): Promise<BrowserSession> {
  return aitdeV2.post('/browser-sessions', payload)
}

export function stopBrowserSession(id: string): Promise<BrowserSession> {
  return aitdeV2.post(`/browser-sessions/${id}/stop`)
}

export async function fetchBrowserSessionEvents(
  id: string,
  signal?: AbortSignal,
): Promise<BrowserSessionEvent[]> {
  const rows = (await aitdeV2.get(`/browser-sessions/${id}/events`, { signal })) as RawBrowserSessionEvent[]
  return (rows ?? []).map(mapEvent)
}

/** Derive a Command IR from observed browser events. */
export function deriveActionPlanFromSession(id: string): Promise<CommandIR> {
  return aitdeV2.post(`/browser-sessions/${id}/derive-action-plan`)
}

// ── Manual assist ──

export interface ManualSession {
  id: string
  status: string
  scenario_version_id: number
  browser_session_id: string | null
}

export interface CreateManualSessionInput {
  run_id: number
  scenario_version_id: number
  browser_session_id?: string
}

export interface ManualStep {
  id: string
  sequence: number
  step_key: string
  status: string
  tester_note: string | null
  evidence_refs_json: Record<string, unknown> | null
}

export interface CompleteManualStepInput {
  status: 'PENDING' | 'DONE' | 'FAILED' | 'BLOCKED' | 'SKIPPED'
  tester_note?: string
  evidence_refs?: unknown[]
}

type RawManualStep = Omit<ManualStep, 'evidence_refs_json'> & {
  evidence_refs_json?: string | null
}

function mapStep(raw: RawManualStep): ManualStep {
  return {
    ...raw,
    evidence_refs_json: parseJson(raw.evidence_refs_json),
  }
}

export function createManualSession(
  scenarioId: number,
  payload: CreateManualSessionInput,
): Promise<ManualSession> {
  return aitdeV2.post(`/scenarios/${scenarioId}/manual-sessions`, payload)
}

export function addManualStep(
  scenarioId: number,
  sessionId: string,
): Promise<{ id: string; sequence: number; status: string }> {
  return aitdeV2.post(`/scenarios/${scenarioId}/manual-sessions/${sessionId}/steps`)
}

export async function fetchManualSteps(
  scenarioId: number,
  sessionId: string,
  signal?: AbortSignal,
): Promise<ManualStep[]> {
  const rows = (await aitdeV2.get(`/scenarios/${scenarioId}/manual-sessions/${sessionId}/steps`, { signal })) as RawManualStep[]
  return (rows ?? []).map(mapStep)
}

export function completeManualStep(
  scenarioId: number,
  sessionId: string,
  stepId: string,
  payload: CompleteManualStepInput,
): Promise<{ id: string; status: string; completed_at: string }> {
  return aitdeV2.post(
    `/scenarios/${scenarioId}/manual-sessions/${sessionId}/steps/${stepId}/complete`,
    payload,
  )
}

// ── Hybrid run ──

export interface HybridRunResult {
  data: { prepared: boolean; reason?: string }
  action: Record<string, unknown>
  oracle: Record<string, unknown>
  cleanup: { status: string } & Record<string, unknown>
}

export function runHybrid(scenarioId: number, payload: { run_id: number }): Promise<HybridRunResult> {
  return aitdeV2.post(`/scenarios/${scenarioId}/hybrid-runs`, payload)
}

// ── UI label maps ──

export const MANUAL_STEP_STATUS_LABELS: Record<string, { label: string; tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info' }> = {
  PENDING: { label: '待处理', tone: 'warning' },
  DONE: { label: '完成', tone: 'success' },
  FAILED: { label: '失败', tone: 'danger' },
  BLOCKED: { label: '受阻', tone: 'info' },
  SKIPPED: { label: '跳过', tone: 'neutral' },
}
