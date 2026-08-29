import { aitdeV2 } from './missions'
import { parseJson } from './json'
import type { CommandIR } from './actionPlans'

// ── AITDE V3.3 Action Healing Proposal (V33-011) ──

export interface HealingProposal {
  id: number
  scenario_adapter_id: number
  command_plan_version_id: number
  proposal_type: string
  /** Backend stores the before/after Command IR as JSON strings; parsed here. */
  before_json: CommandIR | null
  after_json: CommandIR | null
  reason: string
  /** JSON-string list of evidence refs; parsed here. */
  evidence_refs_json: number[]
  status: string
  created_by_type: string
  created_at: string | null
  reviewed_by: number | null
  reviewed_at: string | null
}

type RawHealingProposal = Omit<
  HealingProposal,
  'before_json' | 'after_json' | 'evidence_refs_json'
> & {
  before_json?: string | null
  after_json?: string | null
  evidence_refs_json?: string | null
}

function mapProposal(raw: RawHealingProposal): HealingProposal {
  return {
    ...raw,
    before_json: parseJson<CommandIR>(raw.before_json),
    after_json: parseJson<CommandIR>(raw.after_json),
    evidence_refs_json: parseJson<number[]>(raw.evidence_refs_json) ?? [],
  }
}

export interface HealingProposalListParams {
  scenario_adapter_id?: number
  status?: string
}

export async function fetchHealingProposals(
  params: HealingProposalListParams = {},
  signal?: AbortSignal,
): Promise<HealingProposal[]> {
  const rows = (await aitdeV2.get('/healing-proposals', { params, signal })) as RawHealingProposal[]
  return (rows ?? []).map(mapProposal)
}

export async function approveHealingProposal(id: number): Promise<HealingProposal> {
  const raw = await (aitdeV2.post(`/healing-proposals/${id}/approve`, {}) as Promise<RawHealingProposal>)
  return mapProposal(raw)
}

export async function rejectHealingProposal(id: number): Promise<HealingProposal> {
  const raw = await (aitdeV2.post(`/healing-proposals/${id}/reject`, {}) as Promise<RawHealingProposal>)
  return mapProposal(raw)
}

export const HEALING_PROPOSAL_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  OPEN: { label: '待审', color: 'bg-warning-muted text-warning' },
  APPROVED: { label: '已批准', color: 'bg-status-success-muted text-status-success' },
  REJECTED: { label: '已拒绝', color: 'bg-status-danger-muted text-status-danger' },
  APPLIED: { label: '已应用', color: 'bg-status-success-muted text-status-success' },
}

export const HEALING_PROPOSAL_TYPE_LABELS: Record<string, string> = {
  LOCATOR: '定位器',
  WAIT: '等待',
  NAVIGATION: '导航',
  NON_BUSINESS_ACTION: '非业务动作',
}
