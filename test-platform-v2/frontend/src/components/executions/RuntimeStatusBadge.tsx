import { Badge } from '@/ui'
import { RUNTIME_STATUS_LABELS } from '@/api/executions'

export default function RuntimeStatusBadge({ status }: { status?: string | null }) {
  if (!status) return <Badge variant="outline">—</Badge>
  const meta = RUNTIME_STATUS_LABELS[status]
  return (
    <Badge variant="secondary" className={meta?.color}>
      {meta?.label ?? status}
    </Badge>
  )
}
