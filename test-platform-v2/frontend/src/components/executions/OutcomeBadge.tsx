import { Badge } from '@/ui'
import { OUTCOME_LABELS } from '@/api/executions'

export default function OutcomeBadge({ outcome }: { outcome?: string | null }) {
  if (!outcome) return <Badge variant="outline">—</Badge>
  const meta = OUTCOME_LABELS[outcome]
  return (
    <Badge variant="secondary" className={meta?.color}>
      {meta?.label ?? outcome}
    </Badge>
  )
}
