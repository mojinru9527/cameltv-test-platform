import { useState } from 'react'
import { Badge, Button, Skeleton } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  listAiSuggestions,
  reviewAiSuggestion,
  SUGGESTION_STATUS_LABELS,
  SUGGESTION_TYPE_LABELS,
  type AiSuggestion,
} from '@/api/aiClosedLoop'

/** V38-011 AI Suggestion Inbox: Tester approves / rejects AI suggestions. */
export default function AiSuggestionsPage() {
  useDocumentTitle('AI 建议收件箱')
  const [status, setStatus] = useState<string | 'ALL'>('ALL')
  const [suggestions, setSuggestions] = useState<AiSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [actingId, setActingId] = useState<number | null>(null)

  const load = (signal?: AbortSignal) => {
    setLoading(true)
    listAiSuggestions(status === 'ALL' ? null : status, signal)
      .then((rows) => setSuggestions(rows))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载建议失败')
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }

  useAbortableEffect((signal) => {
    load(signal)
    return signal
  }, [status])

  const review = async (id: number, action: 'APPROVED' | 'REJECTED') => {
    if (actingId !== null) return
    setActingId(id)
    try {
      await reviewAiSuggestion(id, {
        status: action,
        reason: action === 'APPROVED' ? 'reviewer 确认' : 'reviewer 拒绝',
      })
      toast.success(action === 'APPROVED' ? '建议已批准' : '建议已拒绝')
      setSuggestions((rows) =>
        rows.map((r) =>
          r.id === id ? { ...r, status: action === 'APPROVED' ? 'APPROVED' : 'REJECTED' } : r,
        ),
      )
    } catch (err) {
      toast.error((err as Error).message || '处理失败')
    } finally {
      setActingId(null)
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title="AI 建议收件箱" description="Tester 受控的 AI 建议：批准 / 拒绝待处理建议（V38-011）" />
      <div className="flex items-center gap-2">
        <div className="w-44">
          <Select value={status} onValueChange={(v: string) => setStatus(v as string | 'ALL')}>
            <SelectTrigger>
              <SelectValue placeholder="状态筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">全部</SelectItem>
              <SelectItem value="OPEN">待处理</SelectItem>
              <SelectItem value="APPROVED">已批准</SelectItem>
              <SelectItem value="REJECTED">已拒绝</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <span className="text-xs text-muted-foreground">共 {suggestions.length} 条</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-72" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : suggestions.length === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          暂无 AI 建议
        </div>
      ) : (
        <div className="space-y-2">
          {suggestions.map((s) => (
            <div key={s.id} className="rounded-md border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{SUGGESTION_TYPE_LABELS[s.suggestion_type] ?? s.suggestion_type}</Badge>
                <Badge tone="neutral">{SUGGESTION_STATUS_LABELS[s.status] ?? s.status}</Badge>
                <span className="text-xs text-muted-foreground">#{s.id} · 目标 {s.target_type} / {s.target_id}</span>
                <span className="ml-auto text-xs text-muted-foreground">置信度 {(s.confidence * 100).toFixed(0)}%</span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {typeof s.payload?.summary === 'string' ? s.payload.summary : '（无摘要）'}
              </p>
              {s.status === 'OPEN' && (
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={() => review(s.id, 'APPROVED')} disabled={actingId !== null}>
                    {actingId === s.id ? '处理中…' : '批准'}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => review(s.id, 'REJECTED')} disabled={actingId !== null}>
                    拒绝
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
