import { Badge } from '@/ui'
import { FIXTURE_STATUS_LABELS } from '@/api/fixtures'

export interface FixtureStatusBadgeProps {
  status: string
  className?: string
}

/** Status badge for a fixture, using the shared label/colour map. */
export function FixtureStatusBadge({ status, className }: FixtureStatusBadgeProps) {
  const meta = FIXTURE_STATUS_LABELS[status]
  return (
    <Badge variant="secondary" className={className ?? meta?.color}>
      {meta?.label ?? status}
    </Badge>
  )
}
