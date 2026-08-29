import { useState } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton, Textarea } from '@/ui'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchRunAudit,
  submitRunAudit,
  AUDIT_OUTCOME_LABELS,
  type AuditFeedback,
} from '@/api/executions'

const AUDIT_OPTIONS: { value: 'CONFIRMED' | 'FALSE_PASS' | 'FALSE_FAIL'; label: string }[] = [
  { value: 'CONFIRMED', label: '结论正确' },
  { value: 'FALSE_PASS', label: '误报通过' },
  { value: 'FALSE_FAIL', label: '误报失败' },
]

export default function ShadowAuditPanel({ runId }: { runId: number }) {
  const [feedback, setFeedback] = useState<AuditFeedback[]>([])
  const [loading, setLoading] = useState(true)
  const [outcome, setOutcome] = useState<'CONFIRMED' | 'FALSE_PASS' | 'FALSE_FAIL'>('CONFIRMED')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useAbortableEffect((signal) => {
    if (!runId) return
    fetchRunAudit(runId, signal)
      .then((res) => setFeedback(res.items))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) setFeedback([])
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [runId])

  const doSubmit = async () => {
    if (submitting) return
    setSubmitting(true)
    try {
      const row = await submitRunAudit(runId, { audit_outcome: outcome, reason })
      toast.success('已提交审计反馈')
      setFeedback((prev) => [row, ...prev])
      setReason('')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">审计反馈（不改历史结论）</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {AUDIT_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              size="sm"
              variant={outcome === opt.value ? 'primary' : 'secondary'}
              onClick={() => setOutcome(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        <Textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="审计理由（可选）"
          rows={2}
        />
        <Button size="sm" disabled={submitting} onClick={doSubmit}>
          提交反馈
        </Button>

        <div className="space-y-1 border-t pt-3">
          {loading ? (
            <Skeleton className="h-6 w-full" />
          ) : feedback.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无审计反馈。</p>
          ) : (
            feedback.map((f) => (
              <div key={f.id} className="flex items-center gap-2 text-sm">
                <Badge
                  className={
                    AUDIT_OUTCOME_LABELS[f.audit_outcome]?.color ?? 'bg-muted text-muted-foreground'
                  }
                  variant="secondary"
                >
                  {AUDIT_OUTCOME_LABELS[f.audit_outcome]?.label ?? f.audit_outcome}
                </Badge>
                <span className="text-muted-foreground">{f.reason || '—'}</span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
