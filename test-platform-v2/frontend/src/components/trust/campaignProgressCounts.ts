import type { Campaign } from '@/api/continuous'

/**
 * Campaign execution progress. Derived defensively from the Campaign payload the backend
 * exposes — per-scenario runtime status is not returned, so status is inferred from
 * run_id presence plus the campaign-level status.
 */

export interface CampaignProgressCounts {
  selected: number
  queued: number
  running: number
  finished: number
}

export type CampaignGateState = 'WAITING' | 'EVALUATED'

const FINISHED_STATUSES: ReadonlySet<string> = new Set<string>([
  'EVALUATED',
  'COMPLETED',
  'FINISHED',
  'DONE',
  'SUCCESS',
  'PASSED',
  'FAILED',
])

const RUNNING_STATUSES: ReadonlySet<string> = new Set<string>([
  'RUNNING',
  'EXECUTING',
  'IN_PROGRESS',
])

export function deriveCampaignProgress(campaign: Campaign | null | undefined): CampaignProgressCounts {
  const scenarios = campaign?.scenarios ?? []
  const selected = scenarios.length
  const started = scenarios.filter((s) => s.run_id != null).length
  const status = (campaign?.status ?? '').toUpperCase()
  const finished = FINISHED_STATUSES.has(status) ? started : 0
  const running = RUNNING_STATUSES.has(status) ? Math.max(0, started - finished) : 0
  const queued = Math.max(0, selected - started)
  return { selected, queued, running, finished }
}

export function deriveCampaignGate(campaign: Campaign | null | undefined): CampaignGateState {
  const status = (campaign?.status ?? '').toUpperCase()
  return FINISHED_STATUSES.has(status) ? 'EVALUATED' : 'WAITING'
}
