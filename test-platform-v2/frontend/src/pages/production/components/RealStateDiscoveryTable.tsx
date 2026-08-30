import { Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { parseMaybeObject } from '../utils'
import type { Journey, JourneyStep } from '@/api/production'

interface RealStateDiscoveryTableProps {
  journeys: Journey[]
  loading?: boolean
  /** Optional step counts/groups keyed by journey id, populated after timeline expansion. */
  stepsByJourney?: Record<number, JourneyStep[]>
}

/**
 * Tabular view of observed journeys / their discovered real-world steps.
 */
export function RealStateDiscoveryTable({
  journeys,
  loading = false,
  stepsByJourney = {},
}: RealStateDiscoveryTableProps) {
  if (loading) return <Skeleton className="h-24 w-full" />
  if (journeys.length === 0) {
    return <p className="py-4 text-sm text-muted-foreground">暂无生产真实状态数据。</p>
  }

  return (
    <div className="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Journey</TableHead>
            <TableHead>Hash</TableHead>
            <TableHead>Session</TableHead>
            <TableHead>步骤数</TableHead>
            <TableHead>事件类型</TableHead>
            <TableHead>URL</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {journeys.map((journey) => {
            const steps = stepsByJourney[journey.id] ?? []
            const firstStep = steps[0]
            const source = parseMaybeObject(journey.source_ref_json)
            return (
              <TableRow key={journey.id}>
                <TableCell className="max-w-[22ch] truncate font-medium">
                  {journey.name || `Journey #${journey.id}`}
                </TableCell>
                <TableCell className="font-mono text-xs">{journey.journey_hash}</TableCell>
                <TableCell className="font-mono">#{journey.session_id}</TableCell>
                <TableCell>{steps.length}</TableCell>
                <TableCell>
                  <span className="line-clamp-1 font-mono text-xs text-muted-foreground">
                    {firstStep ? firstStep.event_type : '-'}
                  </span>
                </TableCell>
                <TableCell className="max-w-[32ch]">
                  <span className="line-clamp-1 font-mono text-xs text-muted-foreground">
                    {firstStep?.url_template ?? (typeof source?.name === 'string' ? source.name : '-')}
                  </span>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
