import api from './client'

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

const BASE = '/ops/deployments'

export async function fetchOpsDeployments(signal?: AbortSignal): Promise<OpsDeployment[]> {
  return api.get(BASE, { signal })
}

export async function fetchOpsDeploymentEvents(
  deploymentId: string,
  signal?: AbortSignal,
): Promise<OpsDeploymentEvent[]> {
  return api.get(`${BASE}/${deploymentId}/events`, { signal })
}
