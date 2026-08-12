import { useCallback, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/ui'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import {
  ArrowLeft,
  RotateCcw,
  Plus,
  Play,
  Trash2,
  CheckCircle2,
  XCircle,
  MinusCircle,
  StopCircle,
  Pause,
  Link2,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import EmptyState from '@/components/EmptyState'
import TriagePanel from '@/components/TriagePanel'
import { SkeletonText, SkeletonPage } from '@/components/ui/skeleton'
import { autoExecutePlan, deletePlan, executeCase, executeAllCases, fetchExecutions, fetchPlan, removeCasesFromPlan, updatePlan } from '@/api/testplan'
import { fetchEnvironments } from '@/api/environment'
import useAbortableEffect, { rethrowUnlessAborted } from '@/hooks/useAbortableEffect'
import AddCasesModal from './AddCasesModal'
import PlanDrawer from './PlanDrawer'
import { executionStatusLabel } from './executionStatus'

const STATUS_COLORS: Record<string, { tone: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; className?: string }> = {
  pass: { tone: 'success' },
  fail: { tone: 'danger' },
  skip: { tone: 'warning' },
  block: { tone: 'neutral' },
  pending: { tone: 'neutral' },
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pass: <CheckCircle2 className="size-3 text-status-success" />,
  fail: <XCircle className="size-3 text-destructive" />,
  skip: <MinusCircle className="size-3 text-status-warning" />,
  block: <StopCircle className="size-3 text-muted-foreground" />,
  pending: <Pause className="size-3 text-muted-foreground" />,
}

const PLAN_STATUS: Record<string, { tone: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; label: string }> = {
  draft: { tone: 'neutral', label: '草稿' },
  active: { tone: 'success', label: '进行中' },
  completed: { tone: 'neutral', label: '已完成' },
  archived: { tone: 'neutral', label: '已归档' },
}

// Batch 148 (C147-2): 失败阶段中文映射（与后端 error_type 对齐）
const ERROR_TYPE_LABELS: Record<string, string> = {
  INVALID_CASE: '用例校验',
  TARGET_POLICY: '目标策略/URL',
  POLICY_DENIED: '策略拦截',
  TIMEOUT: '请求超时',
  NETWORK_ERROR: '网络连接',
  ASSERTION_FAILED: '断言失败',
  EXECUTION_ERROR: '执行异常',
}

const errorTypeLabel = (t?: string) => (t && ERROR_TYPE_LABELS[t]) || t || '-'

export default function PlanDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const planId = Number(id)

  const [plan, setPlan] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [execModal, setExecModal] = useState<{ open: boolean; pcase: any }>({ open: false, pcase: null })
  const [execStatus, setExecStatus] = useState('')
  const [execNotes, setExecNotes] = useState('')
  const [execSaving, setExecSaving] = useState(false)
  const [executions, setExecutions] = useState<any>({ total: 0, items: [] })
  const [execLoading, setExecLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deletePlanOpen, setDeletePlanOpen] = useState(false)
  const [execAllLoading, setExecAllLoading] = useState(false)
  const [execScopeOpen, setExecScopeOpen] = useState(false)
  const [execScope, setExecScope] = useState<'all' | 'api'>('all')
  const [autoExecuting, setAutoExecuting] = useState(false)
  const [environments, setEnvironments] = useState<any[]>([])
  const [selectedEnv, setSelectedEnv] = useState('__none__')

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    try {
      const d: any = await fetchPlan(planId, signal)
      if (!signal?.aborted) setPlan(d)
    } catch (error) {
      rethrowUnlessAborted(error, signal)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [planId])

  const loadExecutions = useCallback(async (signal?: AbortSignal) => {
    setExecLoading(true)
    try {
      const d: any = await fetchExecutions(planId, undefined, signal)
      if (!signal?.aborted) setExecutions(d)
    } catch (error) {
      rethrowUnlessAborted(error, signal)
    } finally {
      if (!signal?.aborted) setExecLoading(false)
    }
  }, [planId])

  useAbortableEffect((signal) => { void load(signal) }, [load])
  useAbortableEffect((signal) => { void loadExecutions(signal) }, [loadExecutions])

  const loadEnvironments = useCallback(async (signal?: AbortSignal) => {
    try {
      const envs: any = await fetchEnvironments(signal)
      if (signal?.aborted) return
      setEnvironments(envs || [])
      // 只有一个环境时自动选中，减少一步操作
      if (envs?.length === 1) setSelectedEnv(String(envs[0].id))
    } catch (error) {
      rethrowUnlessAborted(error, signal)
    }
  }, [])

  useAbortableEffect((signal) => { void loadEnvironments(signal) }, [loadEnvironments])

  const doDeletePlan = async () => {
    await deletePlan(planId)
    toast.success('计划已删除')
    navigate('/testplan')
  }

  const doUpdateStatus = async (status: string) => {
    await updatePlan(planId, { status })
    toast.success('状态已更新')
    load()
  }

  const doToggleAutoDefect = async () => {
    await updatePlan(planId, { auto_defect_on_fail: !plan.auto_defect_on_fail })
    toast.success(plan.auto_defect_on_fail ? '已关闭失败自动链路' : '已开启失败自动链路')
    load()
  }

  const doRemoveCase = async (caseId: number) => {
    await removeCasesFromPlan(planId, [caseId])
    toast.success('已移除')
    setDeleteTarget(null)
    load()
  }

  const selectedEnvId = selectedEnv === '__none__' ? undefined : Number(selectedEnv)
  const hasApiCases = (plan?.cases || []).some((c: any) => c.case_type === 'api')

  const ensureEnvSelected = () => {
    if (hasApiCases && selectedEnvId == null) {
      toast.error('计划包含 API 用例，请先选择执行环境（含 base_url 与变量）')
      return false
    }
    return true
  }

  const doAutoExecute = async () => {
    if (!ensureEnvSelected()) return
    setAutoExecuting(true)
    try {
      const result: any = await autoExecutePlan(planId, selectedEnvId)
      toast.success(`批量执行完成: ${result.executed} 条执行, ${result.passed} 通过, ${result.failed} 失败`)
      load()
      loadExecutions()
    } catch (e: any) {
      toast.error(e?.message || '批量执行失败')
    } finally { setAutoExecuting(false) }
  }

  const doExecute = async () => {
    if (!execModal.pcase) return
    if (!execStatus) {
      toast.error('请选择执行结果')
      return
    }
    setExecSaving(true)
    try {
      await executeCase(planId, execModal.pcase.id, { status: execStatus, notes: execNotes })
      toast.success('执行完成')
      setExecModal({ open: false, pcase: null })
      load()
      loadExecutions()
    } catch {
      // handled by interceptor
    } finally { setExecSaving(false) }
  }

  const openExec = (pcase: any) => {
    setExecModal({ open: true, pcase })
    setExecStatus('')
    setExecNotes('')
  }

  const doExecuteAll = async () => {
    if (!ensureEnvSelected()) return
    setExecAllLoading(true)
    try {
      const result: any = await executeAllCases(planId, selectedEnvId)
      toast.success(`批量执行完成: ${result.passed} 通过, ${result.failed} 失败, ${result.skipped} 跳过`)
      load()
      loadExecutions()
    } catch {
      // handled by interceptor
    } finally { setExecAllLoading(false) }
  }

  if (!plan) {
    return (
      <div className="p-4">
        <SkeletonPage />
      </div>
    )
  }

  const stats = plan.stats || {}
  const passRate = stats.total > 0 ? Math.round(((stats.pass_ || 0) / stats.total) * 100) : 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/testplan')}>
          <ArrowLeft className="size-4" data-icon="inline-start" />
          返回
        </Button>
        <h2 className="text-lg font-semibold tracking-tight">{plan.name}</h2>
        {plan.plan_id && <Badge tone="neutral">{plan.plan_id}</Badge>}
        <Badge tone={PLAN_STATUS[plan.status]?.tone || 'neutral'}>
          {PLAN_STATUS[plan.status]?.label || plan.status}
        </Badge>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          {hasApiCases && (
            <Select value={selectedEnv} onValueChange={setSelectedEnv}>
              <SelectTrigger id="plan-exec-env" className="w-[180px]" aria-label="执行环境">
                <SelectValue placeholder="请选择环境" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">请选择环境</SelectItem>
                {environments.map((e: any) => (
                  <SelectItem key={e.id} value={String(e.id)}>{e.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <label
            className="flex cursor-pointer items-center gap-1.5 text-xs text-muted-foreground"
            title="执行失败时自动生成缺陷、报告并推送通知（需在计划编辑中确认开关语义）"
          >
            <Checkbox
              checked={!!plan.auto_defect_on_fail}
              onCheckedChange={() => void doToggleAutoDefect()}
              aria-label="失败自动转缺陷/报告/通知"
            />
            失败自动链路
          </label>
          <Button
            size="sm"
            variant="primary"
            onClick={() => setExecScopeOpen(true)}
            disabled={!plan.cases?.length}
          >
            <Play className="size-3.5" data-icon="inline-start" />
            执行
          </Button>
          {plan.status === 'draft' && (
            <Button size="sm" onClick={() => doUpdateStatus('active')}>开始执行</Button>
          )}
          {plan.status === 'active' && (
            <Button size="sm" onClick={() => doUpdateStatus('completed')}>标记完成</Button>
          )}
          <Button size="sm" variant="secondary" onClick={() => void load()} aria-label="刷新测试计划详情">
            <RotateCcw className="size-3.5" data-icon="inline-start" />
          </Button>

          <Button size="sm" variant="secondary" onClick={() => setEditOpen(true)}>编辑</Button>
          <AlertDialog open={deletePlanOpen} onOpenChange={setDeletePlanOpen}>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="danger">删除</Button>
            </AlertDialogTrigger>
            <AlertDialogContent size="sm">
              <AlertDialogHeader>
                <AlertDialogTitle>确定删除计划？</AlertDialogTitle>
                <AlertDialogDescription>此操作不可撤销，将同时删除计划下所有执行记录。</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>取消</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={doDeletePlan}>删除</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-12 gap-3">
        <Card size="sm" className="col-span-2">
          <CardContent className="text-center py-3">
            <div className="text-xs text-muted-foreground">总用例</div>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card size="sm" className="col-span-3">
          <CardContent className="py-3">
            <Progress value={passRate} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1 text-center">{passRate}% 通过率</div>
          </CardContent>
        </Card>
        {[
          ['pass', stats.pass_ || 0],
          ['fail', stats.fail || 0],
          ['skip', stats.skip || 0],
          ['block', stats.block || 0],
          ['pending', stats.pending || 0],
        ].map(([key, val]) => (
          <Card key={key} size="sm" className="col-span-1">
            <CardContent className="text-center py-3">
              <div className={cn(
                'text-xl font-bold',
                key === 'pass' && 'text-status-success',
                key === 'fail' && 'text-destructive',
                key === 'skip' && 'text-status-warning'
              )}>
                {val as number}
              </div>
              <div className="text-xs text-muted-foreground">{key}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Description (Descriptions) */}
      <Card size="sm">
        <CardContent className="pt-[var(--card-spacing)]">
          <dl className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">描述</dt>
              <dd className="mt-0.5">{plan.description || '-'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">负责人</dt>
              <dd className="mt-0.5">{plan.assignee_name || '-'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">开始</dt>
              <dd className="mt-0.5">{plan.start_date ? new Date(plan.start_date).toLocaleDateString() : '-'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">截止</dt>
              <dd className="mt-0.5">{plan.due_date ? new Date(plan.due_date).toLocaleDateString() : (plan.end_date ? new Date(plan.end_date).toLocaleDateString() : '-')}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Cases + Executions Tabs */}
      <Card size="sm">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm">用例与执行</CardTitle>
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <Plus className="size-3.5" data-icon="inline-start" />
            添加用例
          </Button>
        </CardHeader>
        <CardContent className="pt-0">
          <Tabs defaultValue="cases">
            <TabsList>
              <TabsTrigger value="cases">用例列表 ({stats.total})</TabsTrigger>
              <TabsTrigger value="executions">执行历史 ({executions.total})</TabsTrigger>
              <TabsTrigger value="triage">失败分诊 ({stats.fail || 0})</TabsTrigger>
            </TabsList>

            {/* Cases Tab */}
            <TabsContent value="cases" className="mt-3">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">#</TableHead>
                      <TableHead>标题</TableHead>
                      <TableHead className="w-[100px]">模块</TableHead>
                      <TableHead className="w-[80px]">状态</TableHead>
                      <TableHead className="w-[140px]">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={9} className="py-8">
                          <SkeletonText lines={4} />
                        </TableCell>
                      </TableRow>
                    ) : (plan.cases || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-8">
                          <EmptyState title="暂无用例" description="点击「添加用例」将用例纳入计划" className="py-0" />
                        </TableCell>
                      </TableRow>
                    ) : (
                      (plan.cases || []).map((r: any) => {
                        const sc = STATUS_COLORS[r.last_status] || { tone: 'neutral' as const }
                        return (
                          <TableRow key={r.id}>
                            <TableCell className="text-muted-foreground">{r.sort_order}</TableCell>
                            <TableCell className="max-w-0 truncate">
                              <div className="flex items-center gap-1">
                                <Badge tone={r.priority === 'P0' ? 'danger' : r.priority === 'P1' ? 'warning' : 'neutral'}>
                                  {r.priority}
                                </Badge>
                                {r.case_type === 'api' && (
                                  <Badge tone="neutral" className="bg-status-accent-muted text-status-accent dark:bg-status-accent-muted dark:text-status-accent">
                                    接口
                                  </Badge>
                                )}
                                <span className="text-xs text-muted-foreground mr-1">{r.case_id_code}</span>
                                <span className="truncate">{r.case_title}</span>
                              </div>
                            </TableCell>
                            <TableCell className="max-w-[100px] truncate">{r.module}</TableCell>
                            <TableCell>
                              <Badge tone={sc.tone} className={sc.className}>
                                {STATUS_ICONS[r.last_status]}
                                <span className="ml-0.5">{executionStatusLabel(r.last_status)}</span>
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Button size="sm" onClick={() => openExec(r)}>
                                  <Play className="size-3.5" data-icon="inline-start" />
                                  执行
                                </Button>
                                <AlertDialog open={deleteTarget === r.case_id} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
                                  <AlertDialogTrigger asChild>
                                    <Button size="icon-xs" variant="ghost" className="text-destructive hover:bg-destructive/10" onClick={() => setDeleteTarget(r.case_id)} aria-label={`从计划中移除用例 ${r.title || r.case_id}`}>
                                      <Trash2 className="size-3" />
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent size="sm">
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>确定移除？</AlertDialogTitle>
                                      <AlertDialogDescription>将从计划中移除此用例。</AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>取消</AlertDialogCancel>
                                      <AlertDialogAction variant="destructive" onClick={() => doRemoveCase(r.case_id)}>移除</AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
                              </div>
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            {/* Executions Tab */}
            <TabsContent value="executions" className="mt-3">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>用例</TableHead>
                      <TableHead className="w-[80px]">结果</TableHead>
                      <TableHead className="w-[200px]">备注</TableHead>
                      <TableHead className="w-[220px]">失败原因</TableHead>
                      <TableHead className="w-[90px]">HTTP 状态</TableHead>
                      <TableHead className="w-[110px]">失败阶段</TableHead>
                      <TableHead className="w-[170px]">时间</TableHead>
                      <TableHead className="w-[110px]">API 任务</TableHead>
                      <TableHead className="w-[80px]">链路</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {execLoading ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-8">
                          <SkeletonText lines={4} />
                        </TableCell>
                      </TableRow>
                    ) : executions.items?.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="py-8">
                          <EmptyState title="暂无执行记录" description="对用例执行测试后将在此显示记录" className="py-0" />
                        </TableCell>
                      </TableRow>
                    ) : (
                      (executions.items || []).map((r: any) => {
                        const sc = STATUS_COLORS[r.status] || { tone: 'neutral' as const }
                        return (
                          <TableRow key={r.id}>
                            <TableCell className="max-w-0 truncate">{r.case_title}</TableCell>
                            <TableCell>
                              <Badge tone={sc.tone} className={sc.className}>{executionStatusLabel(r.status)}</Badge>
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">{r.notes || '-'}</TableCell>
                            <TableCell className="max-w-[220px]">
                              {r.status === 'fail' ? (
                                <span
                                  className="block truncate text-destructive"
                                  title={r.error_message || r.actual_result || '-'}
                                >
                                  {r.error_message || (r.error_type ? errorTypeLabel(r.error_type) : '-')}
                                </span>
                              ) : '-'}
                            </TableCell>
                            <TableCell>
                              {r.status === 'fail' && r.status_code ? (
                                <span className={r.status_code >= 400 ? 'text-destructive' : ''}>{r.status_code}</span>
                              ) : '-'}
                            </TableCell>
                            <TableCell>
                              {r.status === 'fail' && r.error_type ? (
                                <Badge tone="warning">{errorTypeLabel(r.error_type)}</Badge>
                              ) : '-'}
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {r.executed_at ? new Date(r.executed_at).toLocaleString() : '-'}
                            </TableCell>
                            <TableCell>
                              {r.api_task_id ? (
                                <Badge tone="neutral" title="已关联接口执行任务快照（可在接口测试-任务列表查看）">API 任务 #{r.api_task_id}</Badge>
                              ) : '-'}
                            </TableCell>
                            <TableCell>
                              {r.kibana_link ? (
                                <a href={r.kibana_link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline text-xs">
                                  <Link2 className="size-3" />
                                  Kibana
                                </a>
                              ) : r.trace_id ? (
                                <Badge tone="neutral">{r.trace_id}</Badge>
                              ) : (
                                '-'
                              )}
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="triage" className="mt-3">
              <TriagePanel planId={planId} hasFailures={(stats.fail || 0) > 0} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Add Cases Modal */}
      <AddCasesModal
        open={addOpen}
        planId={planId}
        onClose={() => setAddOpen(false)}
        onAdded={() => load()}
      />

      {/* Edit Plan Drawer */}
      <PlanDrawer
        open={editOpen}
        editing={plan}
        onClose={() => setEditOpen(false)}
        onSaved={() => { setEditOpen(false); load() }}
      />

      {/* 执行范围选择弹窗（P2-01：合并批量执行/一键执行为单一执行入口） */}
      <Dialog open={execScopeOpen} onOpenChange={setExecScopeOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>执行计划</DialogTitle>
            <DialogDescription>选择执行范围与目标环境</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium">执行范围</label>
              <Select value={execScope} onValueChange={(v) => setExecScope(v as 'all' | 'api')}>
                <SelectTrigger className="w-full" aria-label="执行范围">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部用例（API/UI 自动，人工标记跳过）</SelectItem>
                  <SelectItem value="api">仅 API 用例</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {hasApiCases && (
              <div>
                <label className="mb-1.5 block text-sm font-medium">执行环境</label>
                <Select value={selectedEnv} onValueChange={setSelectedEnv}>
                  <SelectTrigger className="w-full" aria-label="执行环境">
                    <SelectValue placeholder="请选择环境" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">请选择环境</SelectItem>
                    {environments.map((e: any) => (
                      <SelectItem key={e.id} value={String(e.id)}>{e.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setExecScopeOpen(false)}>取消</Button>
            <Button
              disabled={execAllLoading || autoExecuting}
              onClick={() => {
                setExecScopeOpen(false)
                if (execScope === 'api') void doAutoExecute()
                else void doExecuteAll()
              }}
            >
              {execAllLoading || autoExecuting ? '执行中...' : '确认执行'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Execute Dialog */}

      <Dialog open={execModal.open} onOpenChange={(open) => { if (!open) setExecModal({ open: false, pcase: null }) }}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>执行用例: {execModal.pcase?.case_title || ''}</DialogTitle>
            <DialogDescription>记录本次执行结果</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium">执行结果</label>
              <Select value={execStatus} onValueChange={setExecStatus}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="选择结果" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pass">通过</SelectItem>
                  <SelectItem value="fail">失败</SelectItem>
                  <SelectItem value="skip">跳过</SelectItem>
                  <SelectItem value="block">阻塞</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">备注</label>
              <Textarea
                rows={3}
                value={execNotes}
                onChange={(e) => setExecNotes(e.target.value)}
                placeholder="执行备注、截图链接等"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setExecModal({ open: false, pcase: null })}>取消</Button>
            <Button disabled={execSaving} onClick={doExecute}>
              {execSaving ? '保存中...' : '确认'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
