import { Badge, type BadgeTone } from '@/ui'
import type { DataPlan } from '@/api/dataPlans'
import {
  type SuccessStage,
  SUCCESS_STAGE_LABELS,
  isDataReady,
  normalizeSuccessStage,
  successStageFromDataPlan,
} from './successStage'

export interface SuccessStageBadgeProps {
  stage?: SuccessStage | string | null
  plan?: DataPlan | null
  className?: string
}

function toneFor(stage: SuccessStage): BadgeTone {
  if (stage === 'VERIFIED') return 'success'
  if (stage === 'VALIDATED') return 'info'
  if (stage === 'EXECUTED') return 'info'
  return 'warning' // GENERATED
}

/**
 * Renders the data-plan success stage (Generated → Validated → Executed → Verified).
 * A plan that is only GENERATED is never shown as "Data Ready"; the "尚未就绪" link
 * appears until the plan reaches VERIFIED.
 */
export function SuccessStageBadge({ stage, plan, className }: SuccessStageBadgeProps) {
  const resolved = stage != null ? normalizeSuccessStage(stage) : successStageFromDataPlan(plan)
  const ready = isDataReady(resolved)

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className ?? ''}`}>
      <Badge tone={toneFor(resolved)}>{SUCCESS_STAGE_LABELS[resolved]}</Badge>
      {!ready && <span className="text-xs text-muted-foreground">尚未就绪</span>}
    </div>
  )
}
