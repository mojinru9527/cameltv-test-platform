import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
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
import {
  fetchMissionLifecycle,
  type MissionLifecycleCase,
} from '@/api/missions'
import { missionKeys } from '@/lib/queryClient'
import { fetchCurrentContract } from '@/api/contract'
import { useAitdeV3Enabled } from '@/config/aitde'
import OutcomeBadge from '@/components/executions/OutcomeBadge'
import { Sparkles, Check, X, FileText, Play, History } from '@/lib/icons'

const CASE_TYPE_LABELS: Record<string, string> = {
  FUNCTIONAL: '功能',
  API: '接口',
  UI: 'UI 自动化',
  UNCLASSIFIED: '未分类',
}

const REQUIREMENT_ROLE_LABELS: Record<string, string> = {
  NEW: '新增',
  CHANGED: '变更',
  IMPACTED_BASELINE: '受影响基线',
  UNCLASSIFIED: '未分类',
}

export default function MissionScenariosPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const navigate = useNavigate()
  const aitdeEnabled = useAitdeV3Enabled()
  useDocumentTitle('场景')

  const [rows, setRows] = useState<ScenarioRow[]>([])
  const [loading, setLoading] = useState(true)
  const [reloadVersion, setReloadVersion] = useState(0)
  const [generating, setGenerating] = useState(false)
  const [activeRow, setActiveRow] = useState<ScenarioRow | null>(null)
  const [detail, setDetail] = useState<ScenarioDetail | null>(null)
  const [projection, setProjection] = useState<FunctionalProjection | null>(null)
  const [viewOpen, setViewOpen] = useState(false)

  const lifecycleQuery = useQuery({
    queryKey: missionKeys.lifecycle(missionId),
    queryFn: ({ signal }) => fetchMissionLifecycle(missionId, signal),
    enabled: Number.isFinite(missionId) && missionId > 0,
  })
  const caseFacts = useMemo<Record<number, MissionLifecycleCase>>(
    () => Object.fromEntries(
      (lifecycleQuery.data?.cases ?? []).map((item) => [item.scenario_id, item]),
    ),
    [lifecycleQuery.data],
  )

  const reload = () => {
    setReloadVersion((version) => version + 1)
    void lifecycleQuery.refetch()
  }

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionScenarios(missionId, signal)
      .then((scenarioRows) => {
        setRows(scenarioRows)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, reloadVersion])

  const doGenerate = async () => {
    if (generating) return
    setGenerating(true)
    try {
      // generate requires a FROZEN contract version id
      const contract = await fetchCurrentContract(missionId)
      if (!contract?.version || contract.version.status !== 'FROZEN') {
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
                <TableHead>类型</TableHead>
                <TableHead>模块 / 需求</TableHead>
                <TableHead>评审</TableHead>
                <TableHead>执行事实</TableHead>
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
                  const fact = caseFacts[r.id]
                  return (
                    <TableRow key={r.id}>
                      <TableCell>
                        <p className="font-medium">{r.title}</p>
                        <p className="font-mono text-xs text-muted-foreground">{r.scenario_key}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {CASE_TYPE_LABELS[fact?.case_type] ?? fact?.case_type ?? '未分类'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <p className="text-sm">{fact?.module_key || '未填写模块'}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {REQUIREMENT_ROLE_LABELS[fact?.requirement_role] ?? fact?.requirement_role ?? '未分类'}
                          {' · '}来源 {fact?.source_ref_count ?? 0}
                        </p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={st?.color}>
                          {st?.label ?? r.review_status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap items-center gap-2">
                          <OutcomeBadge outcome={fact?.latest_outcome ?? null} />
                          <span className="text-xs text-muted-foreground">
                            执行 {fact?.run_count ?? 0} · 证据 {fact?.verified_evidence_count ?? 0}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {aitdeEnabled && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => navigate(`/missions/${missionId}/scenarios/${r.id}/manual`)}
                            >
                              <Play className="size-3.5" /> 执行
                            </Button>
                          )}
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
                          {fact?.latest_run_id && fact.replay_count > 0 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              aria-label={`回放 Run #${fact.latest_run_id}`}
                              title={`回放 Run #${fact.latest_run_id}`}
                              onClick={() => navigate(`/executions/${fact.latest_run_id}/replay`)}
                            >
                              <History className="size-3.5" /> 回放
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
