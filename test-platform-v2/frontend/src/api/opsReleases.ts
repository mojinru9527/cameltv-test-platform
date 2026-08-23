import api from './client'
import type { AxiosRequestConfig } from 'axios'

export interface OpsDeployment {
  id: string
  release_id: string
  manifest_sha256: string
  environment: string
  state: string
  created_at: string
}

export interface OpsDeploymentEvent {
  sequence: number
  from_state: string
  to_state: string
  phase: string
  reason: string
  actor: string
  created_at: string
}

export interface OpsActionResult {
  action: string
  ok: boolean
  summary: string
  logs: string
  deployment_id: string
  state: string
  backups: { id: string; filename: string; created_at: string }[]
}

const BASE = '/ops/deployments'
type ToastAwareRequestConfig = AxiosRequestConfig & { suppressErrorToast: boolean }

function quietRequest(signal?: AbortSignal): ToastAwareRequestConfig {
  return { signal, suppressErrorToast: true }
}

export async function fetchOpsDeployments(signal?: AbortSignal): Promise<OpsDeployment[]> {
  return api.get(BASE, quietRequest(signal))
}

export async function fetchOpsDeploymentEvents(
  deploymentId: string,
  signal?: AbortSignal,
): Promise<OpsDeploymentEvent[]> {
  return api.get(`${BASE}/${deploymentId}/events`, quietRequest(signal))
}

// ── 写操作（release-platform batch）─────────────────────────────────────

export interface SubmitReleasePayload {
  release_id: string
  environment: 'test' | 'production'
  image_tag: string
  manifest_json: string
  note?: string
}

export async function submitOpsRelease(
  payload: SubmitReleasePayload,
): Promise<OpsActionResult> {
  return api.post(BASE, payload)
}

export async function publishOpsDeployment(
  deploymentId: string,
  payload: { image_tag: string; note?: string },
): Promise<OpsActionResult> {
  return api.post(`${BASE}/${deploymentId}/publish`, payload)
}

export async function rollbackOpsDeployment(
  deploymentId: string,
  payload: { image_tag: string; note?: string },
): Promise<OpsActionResult> {
  return api.post(`${BASE}/${deploymentId}/rollback`, payload)
}

export async function backupOpsDeployment(
  deploymentId: string,
): Promise<OpsActionResult> {
  return api.post(`${BASE}/${deploymentId}/backup`, {})
}

export async function opsHealthCheck(): Promise<OpsActionResult> {
  return api.post(`${BASE}/health-check`, {})
}
