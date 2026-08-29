import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Button, Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  analyzeMissionScope,
  fetchMissionScope,
  reviewMissionScope,
  DECISION_LABELS,
  REVIEW_LABELS,
  RISK_LABELS,
  SCOPE_TYPE_LABELS,
  type ScopeItem,
  type ScopeSummary,
} from '@/api/scope'
import { Sparkles, Check, X } from '@/lib/icons'

export default function MissionScopePage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('范围')

  const [items, setItems] = useState<ScopeItem[]>([])
  const [summary, setSummary] = useState<ScopeSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [pendingKey, setPendingKey] = useState<string | null>(null)

  const reload = () => setLoading(true)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionScope(missionId)
      .then((res) => {
        setItems(res.items)
        setSummary(res.summary)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, loading])

  const doAnalyze = async () => {
    if (analyzing) return
    setAnalyzing(true)
    try {
      await analyzeMissionScope(missionId, { force: true })
      toast.success('Scope 分析完成')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const doReview = async (item: ScopeItem, action: 'approve' | 'reject') => {
    setPendingKey(item.scope_key)
    try {
      await reviewMissionScope(missionId, [
        {
          scope_key: item.scope_key,
          decision: item.decision === 'EXCLUDE' ? 'EXCLUDE' : 'INCLUDE',
          action,
        },
      ])
      toast.success(action === 'approve' ? '已批准' : '已拒绝')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '评审失败')
    } finally {
      setPendingKey(null)
    }
  }

  const progress = summary?.review_progress ?? 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">范围 {summary?.total ?? 0} 项</span>
          <span className="text-muted-foreground">
            已评审 {summary ? summary.approved + summary.rejected : 0}
          </span>
          <span className="text-primary">进度 {Math.round(progress * 100)}%</span>
        </div>
        <Button disabled={analyzing} onClick={doAnalyze}>
          <Sparkles className="size-4" /> {analyzing ? '分析中…' : '分析范围'}
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>范围项</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>风险</TableHead>
                <TableHead>决策</TableHead>
                <TableHead>深度</TableHead>
                <TableHead>评审</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="py-10 text-center text-muted-foreground">
                    尚未生成 Scope。点击「分析范围」生成 AI 建议后评审。
                  </TableCell>
                </TableRow>
              ) : (
                items.map((s) => {
                  const rev = REVIEW_LABELS[s.review_status]
                  const dec = DECISION_LABELS[s.decision]
                  return (
                    <TableRow key={s.scope_key}>
                      <TableCell>
                        <p className="font-medium">{s.name}</p>
                        <p className="mt-0.5 max-w-md truncate text-xs text-muted-foreground">
                          {s.reason}
                        </p>
                      </TableCell>
                      <TableCell>{SCOPE_TYPE_LABELS[s.scope_type] ?? s.scope_type}</TableCell>
                      <TableCell>{RISK_LABELS[s.risk_level] ?? s.risk_level}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={dec?.color}>
                          {dec?.label ?? s.decision}
                        </Badge>
                      </TableCell>
                      <TableCell>{s.test_depth}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={rev?.color}>
                          {rev?.label ?? s.review_status}
                        </Badge>
                      </TableCell>
                      <TableCell>{Math.round(s.ai_confidence * 100)}%</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {s.review_status !== 'APPROVED' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={pendingKey === s.scope_key}
                              onClick={() => doReview(s, 'approve')}
                            >
                              <Check className="size-3.5" /> 批准
                            </Button>
                          )}
                          {s.review_status !== 'REJECTED' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={pendingKey === s.scope_key}
                              onClick={() => doReview(s, 'reject')}
                            >
                              <X className="size-3.5" /> 拒绝
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
