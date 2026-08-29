import { Badge } from '@/ui'
import { type BrowserSessionEvent } from '@/api/browserInteractions'
import { JsonBlock } from './JsonView'

export interface ObservationTimelineProps {
  events: BrowserSessionEvent[]
  loading?: boolean
}

/**
 * Vertical, ordered timeline of browser-observation events. `semantic_target_json`
 * is server-side redacted and rendered fully as readable key/value so a reviewer
 * never loses the observed target.
 */
export function ObservationTimeline({ events, loading }: ObservationTimelineProps) {
  const sorted = events.slice().sort((a, b) => a.sequence - b.sequence)

  if (loading) {
    return (
      <div className="space-y-2" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-md border bg-muted/40" />
        ))}
      </div>
    )
  }

  if (sorted.length === 0) {
    return (
      <div className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
        暂无观察事件。启动浏览器会话后，事件会按到达顺序显示。
      </div>
    )
  }

  return (
    <ol className="space-y-3">
      {sorted.map((event, index) => (
        <li key={event.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" />
            {index < sorted.length - 1 && <span className="w-px flex-1 bg-border" />}
          </div>
          <div className="min-w-0 flex-1 rounded-md border px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">#{event.sequence}</span>
              <Badge variant="outline" className="font-mono text-[11px]">
                {event.event_type}
              </Badge>
              <span className="font-mono text-[11px] text-muted-foreground">{event.id}</span>
            </div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <JsonBlock label="语义目标 (semantic_target_json)" data={event.semantic_target_json} />
              <JsonBlock label="引用载荷 (payload_ref_json)" data={event.payload_ref_json} />
            </div>
          </div>
        </li>
      ))}
    </ol>
  )
}
