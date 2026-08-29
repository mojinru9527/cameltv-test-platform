import { Badge } from '@/ui'

export interface OracleChangeGuardBadgeProps {
  /** Whether the oracle (关键断言) set changed between the compared revisions. */
  changed: boolean
  /** Optional summary text shown next to the badge. */
  detail?: string
}

/**
 * Guards an oracle change between a baseline and a candidate revision.
 * An oracle change must never be silently accepted — surface it explicitly
 * so a reviewer treats the healing proposal as risk-bearing.
 */
export function OracleChangeGuardBadge({ changed, detail }: OracleChangeGuardBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      {changed ? (
        <Badge tone="warning">Oracle 已变更</Badge>
      ) : (
        <Badge tone="success">Oracle 未变更</Badge>
      )}
      {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
    </div>
  )
}
