import type { DataPlan } from '@/api/dataPlans'

/**
 * Success lifecycle stage for a data plan. The plan may be "Generated" but must never be
 * shown as "Data Ready" (VERIFIED) until it has actually been verified in the DB runtime.
 */

export enum SuccessStage {
  GENERATED = 'GENERATED',
  VALIDATED = 'VALIDATED',
  EXECUTED = 'EXECUTED',
  VERIFIED = 'VERIFIED',
}

export const SUCCESS_STAGE_LABELS: Record<SuccessStage, string> = {
  GENERATED: '计划已生成',
  VALIDATED: '已验证',
  EXECUTED: '已执行',
  VERIFIED: '数据就绪(已核验)',
}

/** Only the VERIFIED stage means the data is actually ready for use. */
export function isDataReady(stage: SuccessStage): boolean {
  return stage === SuccessStage.VERIFIED
}

const VALID_STAGES: ReadonlySet<string> = new Set<string>(Object.values(SuccessStage))

export function normalizeSuccessStage(stage: SuccessStage | string | null | undefined): SuccessStage {
  if (typeof stage === 'string' && VALID_STAGES.has(stage)) return stage as SuccessStage
  return SuccessStage.GENERATED
}

/**
 * Derive the success stage from the DataPlan payload. VERIFIED requires the plan to be
 * COMPLETED *and* to contain at least one successful VERIFY step — otherwise the plan is
 * only Generated / Validated / Executed and must not be advertised as data-ready.
 */
export function successStageFromDataPlan(plan: DataPlan | null | undefined): SuccessStage {
  if (!plan) return SuccessStage.GENERATED
  const status = plan.status.toUpperCase()
  const hasVerifiedStep = (plan.steps ?? []).some(
    (s) => s.step_type.toUpperCase() === 'VERIFY' && s.status.toUpperCase() === 'SUCCESS',
  )
  if (status === 'COMPLETED' && hasVerifiedStep) return SuccessStage.VERIFIED
  if (status === 'COMPLETED' || status === 'EXECUTING') return SuccessStage.EXECUTED
  if (status === 'APPROVED') return SuccessStage.VALIDATED
  return SuccessStage.GENERATED
}
