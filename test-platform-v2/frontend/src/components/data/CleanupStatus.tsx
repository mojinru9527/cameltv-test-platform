import { Badge } from '@/ui'
import { Trash2 } from '@/lib/icons'
import { FIXTURE_STATUS_LABELS } from '@/api/fixtures'

export interface CleanupStatusProps {
  cleanupStatus: string | null
  className?: string
}

/** Displays the fixture cleanup state (e.g. pending / cleaned / failed). */
export function CleanupStatus({ cleanupStatus, className }: CleanupStatusProps) {
  if (!cleanupStatus) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
        <Trash2 className="size-4" />
        <Badge variant="outline" className={className}>未清理</Badge>
      </span>
    )
  }
  const meta = FIXTURE_STATUS_LABELS[cleanupStatus]
  return (
    <span className="inline-flex items-center gap-1.5 text-sm">
      <Trash2 className="size-4 text-muted-foreground" />
      <Badge variant="secondary" className={className ?? meta?.color}>
        {meta?.label ?? cleanupStatus}
      </Badge>
    </span>
  )
}
