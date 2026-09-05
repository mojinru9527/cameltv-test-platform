import { aitdeV2 } from './missions'

export interface ContractRule {
  rule_key: string
  title?: string
  kind: string
  statement?: string
  risk_level?: string
  source_type?: string
}

export interface ContractOutcome {
  outcome_key: string
  statement?: string
  source_type?: string
}

export interface ContractSnapshot {
  schema_version: string
  mission_id: number
  scope_revision: string
  rules: ContractRule[]
  required_outcomes: ContractOutcome[]
}

export interface ContractVersion {
  id: number
  contract_id: number
  version_no: number
  status: 'DRAFT' | 'REVIEWING' | 'FROZEN' | 'SUPERSEDED' | string
  content_hash: string
  /** 已解析的契约快照；畸形历史数据由后端降级为 null */
  snapshot?: ContractSnapshot | null
  created_at: string | null
  approved_at: string | null
}

export interface CurrentContract {
  contract_id: number
  name: string
  version_no: number
  version: ContractVersion | null
}

export function generateContract(
  missionId: number,
  payload: { model?: string; force?: boolean } = {},
): Promise<{ contract_id: number; version_no: number; version_id: number }> {
  return aitdeV2.post(`/missions/${missionId}/contracts/generate`, payload)
}

/**
 * 契约尚未生成时后端返回 HTTP 200 + 业务码 404，这是合法空态而非传输错误：
 * 解析为 `null` 让页面显示「尚未生成 Test Contract」。其余失败照常 reject，
 * 由页面渲染 ErrorState，不得静默降级为空数据。
 */
export async function fetchCurrentContract(
  missionId: number,
  signal?: AbortSignal,
): Promise<CurrentContract | null> {
  try {
    return await aitdeV2.get(`/missions/${missionId}/contract`, { signal })
  } catch (err) {
    const e = err as { code?: unknown; response?: { status?: unknown } } | null
    if (e?.code === 404 || e?.response?.status === 404) return null
    throw err
  }
}

export function fetchContractVersions(contractId: number): Promise<ContractVersion[]> {
  return aitdeV2.get(`/contracts/${contractId}/versions`)
}

export function freezeContract(
  contractId: number,
  expected_version: number,
): Promise<{ version_no: number; status: string; contract_id: number }> {
  return aitdeV2.post(`/contracts/${contractId}/freeze`, {
    expected_version,
    confirm: true,
  })
}

export const CONTRACT_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'bg-muted text-muted-foreground' },
  REVIEWING: { label: '评审中', color: 'bg-status-warning-muted text-status-warning' },
  FROZEN: { label: '已冻结', color: 'bg-status-success-muted text-status-success' },
  SUPERSEDED: { label: '已取代', color: 'bg-muted text-muted-foreground' },
}

/** 取值须用 `{MAP[v] ?? v}`，未映射的枚举仍原样显示。 */
export const CONTRACT_RULE_KIND_LABEL: Record<string, string> = {
  BUSINESS_RULE: '业务规则',
}

/**
 * `RULE_BASELINE` 是未配置 AI 提供方时确定性提供方的产出口径（最常见路径），
 * `AI_INFERRED` 由 contract_builder_v1 提示词允许，二者都必须有中文映射。
 */
export const CONTRACT_SOURCE_TYPE_LABEL: Record<string, string> = {
  REQUIREMENT_EXPLICIT: '需求明示',
  TESTER_APPROVED: '测试确认',
  RULE_BASELINE: '规则基线',
  AI_INFERRED: 'AI 推断',
}
