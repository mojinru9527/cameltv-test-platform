import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchRunReplay, type RunReplay } from '@/api/executions'
import OutcomeBadge from '@/components/executions/OutcomeBadge'
import RuntimeStatusBadge from '@/components/executions/RuntimeStatusBadge'
import ReplayEvidenceViewer from '@/components/executions/ReplayEvidenceViewer'
import { STEP_STATUS_LABELS } from '@/components/executions/constants'
import { ArrowLeft } from '@/lib/icons'
import { cn } from '@/lib/utils'

function SnapshotBlock({
  label,
  value,
}: {
  label: string
  value: Record<string, unknown> | null | undefined
}) {
  if (!value) return null
  let text: string
  try {
    text = JSON.stringify(value, null, 2)
  } catch {
    text = String(value)
  }
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <pre className="mt-1 max-h-72 overflow-auto rounded bg-muted p-2 text-xs">{text}</pre>
    </div>
  )
}

export default function ReplayPage() {
  const { runId: rawRunId } = useParams()
  const runId = Number(rawRunId)
  const navigate = useNavigate()
  useDocumentTitle(runId ? `回放 Run #${runId}` : '执行回放')

  const [replay, setReplay] = useState<RunReplay | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedStepId, setSelectedStepId] = useState<number | null>(null)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number | null>(null)

  useAbortableEffect((signal) => {
    if (!runId) return
    setLoading(true)
    fetchRunReplay(runId, signal)
      .then((res) => {
        setReplay(res)
        setSelectedStepId(res.view.timeline[0]?.id ?? null)
        setSelectedEvidenceId(res.view.evidence[0]?.id ?? null)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '回放数据加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [runId])

  if (loading || !replay) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-10 w-72" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-[28rem]" />
          <Skeleton className="h-[28rem]" />
          <Skeleton className="h-[28rem]" />
        </div>
      </div>
    )
  }

  const { view } = replay
  const selectedStep = view.timeline.find((s) => s.id === selectedStepId) ?? view.timeline[0]
  const selectedEvidence = view.evidence.find((e) => e.id === selectedEvidenceId) ?? null

  return (
    <div className="space-y-4 p-4">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate(`/executions/${runId}`)}>
          <ArrowLeft className="size-4" /> 返回详情
        </Button>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-[-0.02em]">回放 Run #{runId}</h1>
          <OutcomeBadge outcome={view.outcome} />
          <RuntimeStatusBadge status={view.runtime_status} />
          <Badge variant="outline" className="font-mono">hash {replay.hash.slice(0, 12)}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">时间线</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-1">
              {view.timeline.length === 0 ? (
                <li className="py-6 text-center text-sm text-muted-foreground">无时间线节点。</li>
              ) : (
                view.timeline.map((step) => {
                  const st = STEP_STATUS_LABELS[step.status]
                  const active = selectedStep?.id === step.id
                  return (
                    <li key={step.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedStepId(step.id)}
                        className={cn(
                          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
                          active ? 'bg-muted' : 'hover:bg-muted/60',
                        )}
                      >
                        <span className="font-mono text-xs text-muted-foreground">
                          #{step.sequence}
                        </span>
                        <span className="min-w-0 flex-1 truncate">{step.step_key}</span>
                        <Badge variant="secondary" className={st?.color}>
                          {st?.label ?? step.status}
                        </Badge>
                      </button>
                    </li>
                  )
                })
              )}
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {selectedStep ? `步骤 ${selectedStep.sequence}` : '步骤上下文'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {selectedStep ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{selectedStep.step_key}</span>
                  <Badge variant="outline">{selectedStep.step_type}</Badge>
                  <Badge variant="secondary" className={STEP_STATUS_LABELS[selectedStep.status]?.color}>
                    {STEP_STATUS_LABELS[selectedStep.status]?.label ?? selectedStep.status}
                  </Badge>
                </div>
                {selectedStep.error_type && (
                  <p className="text-xs font-medium text-status-danger">{selectedStep.error_type}</p>
                )}
                {selectedStep.error_message && (
                  <p className="text-sm text-status-danger">{selectedStep.error_message}</p>
                )}
                {selectedStep.trace_id && (
                  <p className="text-xs text-muted-foreground">
                    trace {selectedStep.trace_id}
                    {selectedStep.span_id ? ` · span ${selectedStep.span_id}` : ''}
                  </p>
                )}
                <div className="grid gap-3">
                  <SnapshotBlock label="输入快照" value={selectedStep.input_snapshot_json} />
                  <SnapshotBlock label="输出快照" value={selectedStep.output_snapshot_json} />
                </div>
              </>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">选择时间线查看上下文。</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">证据详情</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {view.evidence.length > 0 ? (
              <>
                <ul className="space-y-1">
                  {view.evidence.map((e) => {
                    const active = selectedEvidence?.id === e.id
                    return (
                      <li key={e.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedEvidenceId(e.id)}
                          className={cn(
                            'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors',
                            active ? 'bg-muted' : 'hover:bg-muted/60',
                          )}
                        >
                          <span className="min-w-0 flex-1 truncate">{e.evidence_type}</span>
                          <span className="font-mono text-muted-foreground">
                            {e.content_hash.slice(0, 8)}…
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
                <ReplayEvidenceViewer evidence={selectedEvidence} />
              </>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">无证据。</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
