import { Badge } from '@/ui'

/** Marks a run that was imported/migrated from a legacy execution pipeline. */
export default function LegacyExecutionBadge({ legacy }: { legacy?: boolean }) {
  if (!legacy) return null
  return <Badge variant="outline" className="bg-muted text-muted-foreground">旧版执行</Badge>
}
