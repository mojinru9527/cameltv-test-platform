import { Badge, Card, CardContent, CardHeader, CardTitle, Progress, Skeleton } from '@/ui'
import type { GapCandidate } from '@/api/production'
import { AlertTriangle, Sparkles } from '@/lib/icons'

interface GapCandidatePanelProps {
  candidates: GapCandidate[]
  loading?: boolean
}

/**
 * Render analyze-gaps proposals, flagging candidates that were auto-approved
 * (i.e. without human sign-off) as risk.
 */
export function GapCandidatePanel({ candidates, loading = false }: GapCandidatePanelProps) {
  if (loading) return <Skeleton className="h-24 w-full" />
  if (candidates.length === 0) {
    return <p className="py-4 text-sm text-muted-foreground">暂无缺口候选。先对该 Journey 执行「分析缺口」。</p>
  }

  return (
    <div className="space-y-2">
      {candidates.map((candidate, i) => {
        const confidencePct = Math.max(0, Math.min(100, Math.round(candidate.confidence * 100)))
        return (
          <Card key={`${candidate.kind}-${i}`} size="sm" className="border-l-4 border-l-status-warning">
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
                {candidate.auto_approved ? <AlertTriangle className="size-4 text-status-danger" /> : <Sparkles className="size-4 text-status-warning" />}
                <span className="truncate">{candidate.title || candidate.kind}</span>
                {candidate.auto_approved && <Badge tone="danger">auto-approved</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-mono">{candidate.kind}</span>
                <span>·</span>
                <span>置信度 {confidencePct}%</span>
              </div>
              <Progress value={confidencePct} tone={candidate.auto_approved ? 'danger' : 'warning'} className="h-1.5" />
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
