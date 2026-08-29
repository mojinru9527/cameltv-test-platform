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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchMissionScenarios,
  generateScenarios,
  fetchScenario,
  reviewScenario,
  fetchFunctionalProjection,
  SCENARIO_REVIEW_LABELS,
  type ScenarioRow,
  type ScenarioDetail,
  type FunctionalProjection,
} from '@/api/scenarios'
import { fetchCurrentContract } from '@/api/contract'
import { Sparkles, Check, X, FileText } from '@/lib/icons'

export default function MissionScenariosPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('场景')

  const [rows, setRows] = useState<ScenarioRow[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activeRow, setActiveRow] = useState<ScenarioRow | null>(null)
  const [detail, setDetail] = useState<ScenarioDetail | null>(null)
  const [projection, setProjection] = useState<FunctionalProjection | null>(null)
  const [viewOpen, setViewOpen] = useState(false)

  const reload = () => setLoading(true)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionScenarios(missionId)
      .then(setRows)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, loading])

  const doGenerate = async () => {
    if (generating) return
    setGenerating(true)
    try {
      // generate requires a FROZEN contract version id
      const contract = await fetchCurrentContract(missionId)
      if (!contract.version || contract.version.status !== 'FROZEN') {
        toast.error('需先冻结 Contract 才能生成场景')
        return
      }
      await generateScenarios(contract.version.id)
      toast.success('场景已生成')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const doReview = async (row: ScenarioRow, action: 'approve' | 'reject') => {
    try {
      await reviewScenario(row.id, action)
      toast.success(action === 'approve' ? '已批准' : '已拒绝')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '评审失败')
    }
  }

  const openView = async (row: ScenarioRow) => {
    setActiveRow(row)
    setViewOpen(true)
    setDetail(null)
    setProjection(null)
    try {
      const [d, p] = await Promise.all([
        fetchScenario(row.id),
        fetchFunctionalProjection(row.id),
      ])
      setDetail(d)
      setProjection(p)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载失败')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">统一 TestScenario + Oracle（建模，不执行）</p>
        <Button variant="secondary" disabled={generating} onClick={doGenerate}>
          <Sparkles className="size-4" /> {generating ? '生成中…' : '生成场景'}
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
                <TableHead>场景</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>风险</TableHead>
                <TableHead>评审</TableHead>
                <TableHead>Oracle</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                    尚未生成场景。冻结 Contract 后点击「生成场景」。
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => {
                  const st = SCENARIO_REVIEW_LABELS[r.review_status]
                  return (
                    <TableRow key={r.id}>
                      <TableCell>
                        <p className="font-medium">{r.title}</p>
                        <p className="font-mono text-xs text-muted-foreground">{r.scenario_key}</p>
                      </TableCell>
                      <TableCell>{r.priority}</TableCell>
                      <TableCell>{r.risk_level}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={st?.color}>
                          {st?.label ?? r.review_status}
                        </Badge>
                      </TableCell>
                      <TableCell>{r.oracle_count}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {r.review_status !== 'APPROVED' && (
                            <Button variant="ghost" size="sm" onClick={() => doReview(r, 'approve')}>
                              <Check className="size-3.5" /> 批准
                            </Button>
                          )}
                          {r.review_status !== 'REJECTED' && (
                            <Button variant="ghost" size="sm" onClick={() => doReview(r, 'reject')}>
                              <X className="size-3.5" /> 拒绝
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" onClick={() => openView(r)}>
                            <FileText className="size-3.5" /> 功能视图
                          </Button>
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

      <Dialog open={viewOpen} onOpenChange={setViewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{activeRow?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            {projection ? (
              <>
                <div>
                  <p className="text-muted-foreground">前置条件</p>
                  <ul className="mt-1 list-disc pl-5">
                    {projection.preconditions.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-muted-foreground">步骤</p>
                  <ul className="mt-1 space-y-1">
                    {projection.steps.map((s) => (
                      <li key={s.step} className="flex gap-2">
                        <span className="font-mono text-xs text-muted-foreground">{s.step}.</span>
                        {s.description}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-muted-foreground">预期结果</p>
                  <ul className="mt-1 list-disc pl-5">
                    {projection.expected_results.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <p className="py-8 text-center text-muted-foreground">加载中…</p>
            )}
            {detail && detail.oracles.length > 0 && (
              <div>
                <p className="text-muted-foreground">Oracles</p>
                <ul className="mt-1 space-y-1">
                  {detail.oracles.map((o) => (
                    <li key={o.id} className="flex items-center gap-2">
                      <Badge variant="outline">{o.oracle_type}</Badge>
                      <span>{o.oracle_key}</span>
                      <span className="text-xs text-muted-foreground">
                        {o.source_type} · {o.required ? '必' : '选'}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
