import { Badge } from '@/ui'
import { KeyRound } from '@/lib/icons'
import type { FixtureLease } from '@/api/fixtures'

export interface LeaseIndicatorProps {
  lease: FixtureLease | null
  /** When set, the fixture is reported as leased by the backend status. */
  leasedByStatus?: boolean
}

/** Shows whether a fixture is currently leased and by which run. */
export function LeaseIndicator({ lease, leasedByStatus = false }: LeaseIndicatorProps) {
  const active = lease && lease.status !== 'RELEASED'

  if (active) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm">
        <KeyRound className="size-4 text-status-warning" />
        <Badge tone="warning">已租用</Badge>
        <span className="font-mono text-xs text-muted-foreground">
          租约 #{lease?.id} · run #{lease?.run_id}
        </span>
      </span>
    )
  }

  if (leasedByStatus) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm">
        <KeyRound className="size-4 text-status-warning" />
        <Badge tone="warning">已租用</Badge>
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
      <KeyRound className="size-4" />
      <Badge variant="outline">未租用</Badge>
    </span>
  )
}
