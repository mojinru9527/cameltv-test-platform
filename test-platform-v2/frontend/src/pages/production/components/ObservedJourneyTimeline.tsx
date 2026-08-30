import { useState } from 'react'
import { Badge, Button, Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchJourney, type Journey, type JourneyDetail } from '@/api/production'
import { normalizeXhrRefs, displayValue, parseMaybeObject } from '../utils'
import { XhrEvidenceViewer } from './XhrEvidenceViewer'
import { ChevronDown, ChevronRight, Layers } from '@/lib/icons'

interface ObservedJourneyTimelineProps {
  journeys: Journey[]
  loading?: boolean
  /** Called whenever a journey detail (with steps) is loaded. */
  onDetail?: (detail: JourneyDetail) => void
}

/** Expandable steps timeline for a list of observed journeys. */
export function ObservedJourneyTimeline({ journeys, loading = false, onDetail }: ObservedJourneyTimelineProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<JourneyDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useAbortableEffect((signal) => {
    if (expandedId == null) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    setDetail(null)
    fetchJourney(expandedId, signal)
      .then((res) => {
        if (!signal.aborted) {
          setDetail(res)
          onDetail?.(res)
        }
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setDetailLoading(false)
      })
    // The hook re-runs the latest closure, so `onDetail` is always fresh even though
    // it is omitted here to prevent a re-fetch on every parent render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedId])

  const toggle = (id: number) => {
    setExpandedId((current) => (current === id ? null : id))
  }

  if (loading) return <Skeleton className="h-24 w-full" />
  if (journeys.length === 0) {
    return <p className="py-4 text-sm text-muted-foreground">暂无观察到的 Journey。</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8" />
          <TableHead>Journey</TableHead>
          <TableHead>Hash</TableHead>
          <TableHead>Session</TableHead>
          <TableHead>摘要</TableHead>
          <TableHead>创建时间</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {journeys.map((journey) => {
          const isExpanded = expandedId === journey.id
          const summary = parseMaybeObject(journey.summary_json)
          return (
            <TableRow key={journey.id}>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`展开 ${journey.name}`}
                  aria-expanded={isExpanded}
                  onClick={() => toggle(journey.id)}
                >
                  {isExpanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
                </Button>
              </TableCell>
              <TableCell className="max-w-[24ch] truncate">
                <button
                  type="button"
                  onClick={() => toggle(journey.id)}
                  className="font-medium text-left hover:text-primary hover:underline"
                >
                  {journey.name || `Journey #${journey.id}`}
                </button>
              </TableCell>
              <TableCell className="font-mono text-xs">{journey.journey_hash}</TableCell>
              <TableCell className="font-mono">#{journey.session_id}</TableCell>
              <TableCell className="max-w-[42ch]">
                <span className="line-clamp-1 text-xs text-muted-foreground">
                  {summary ? displayValue(summary) : '-'}
                </span>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {journey.created_at ? new Date(journey.created_at).toLocaleString() : '-'}
              </TableCell>
              {isExpanded && (
                <TableCell colSpan={6} className="whitespace-normal bg-muted/30">
                  <JourneySteps detail={detail} loading={detailLoading} journeyId={journey.id} />
                </TableCell>
              )}
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

function JourneySteps({ detail, loading, journeyId }: { detail: JourneyDetail | null; loading: boolean; journeyId: number }) {
  const steps = detail?.steps ?? []
  const action = detail ? parseMaybeObject(detail.source_ref_json) : null
  const hasSteps = steps.length > 0

  return (
    <div className="space-y-2 py-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Layers className="size-3.5" />
        {detail ? `Steps（${steps.length}）` : `Journey #${journeyId}`}
        {action && (
          <span className="font-mono text-muted-foreground/70">
            src: {displayValue(action)}
          </span>
        )}
      </div>
      {loading && <Skeleton className="h-16 w-full" />}
      {!loading && !hasSteps && <p className="text-xs text-muted-foreground">该 Journey 无步骤明细。</p>}
      {!loading && hasSteps && (
        <ol className="space-y-2 border-l pl-3">
          {steps.map((step) => {
            const semantic = parseMaybeObject(step.semantic_action)
            const xhrRefs = normalizeXhrRefs(step.xhr_refs)
            return (
              <li key={step.sequence} className="relative rounded-md border bg-card p-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral" className="font-mono">#{step.sequence}</Badge>
                  <Badge tone="info">{step.event_type}</Badge>
                  {step.url_template && (
                    <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground">
                      {step.url_template}
                    </span>
                  )}
                </div>
                {semantic && Object.keys(semantic).length > 0 && (
                  <pre className="mt-2 max-h-32 overflow-auto rounded-md bg-muted/30 p-2 font-mono text-xs whitespace-pre-wrap break-all text-muted-foreground">
                    {displayValue(semantic)}
                  </pre>
                )}
                {xhrRefs.length > 0 && (
                  <div className="mt-2">
                    <XhrEvidenceViewer xhrRefs={xhrRefs} />
                  </div>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}
