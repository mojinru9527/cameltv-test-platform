import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
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
import { SkeletonText, SkeletonPage } from '@/components/ui/skeleton'
import { autoExecutePlan, deletePlan, executeCase, fetchExecutions, fetchPlan, removeCasesFromPlan, updatePlan } from '@/api/testplan'
import AddCasesModal from './AddCasesModal'
import PlanDrawer from './PlanDrawer'

const STATUS_COLORS: Record<string, { variant: 'default' | 'destructive' | 'secondary' | 'outline'; className?: string }> = {
  pass: { variant: 'default', className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  fail: { variant: 'destructive' },
  skip: { variant: 'secondary', className: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' },
  block: { variant: 'outline' },
  pending: { variant: 'outline' },
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pass: <CheckCircle2 className="size-3 text-green-600" />,
  fail: <XCircle className="size-3 text-destructive" />,
  skip: <MinusCircle className="size-3 text-orange-500" />,
  block: <StopCircle className="size-3 text-muted-foreground" />,
  pending: <Pause className="size-3 text-muted-foreground" />,
}

const PLAN_STATUS: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
  draft: { variant: 'secondary', label: '草稿' },
  active: { variant: 'default', label: '进行中' },
  completed: { variant: 'destructive', label: '已完成' },
  archived: { variant: 'outline', label: '已归档' },
}

export default function PlanDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const planId = Number(id)

  const [plan, setPlan] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [execModal, setExecModal] = useState<{ open: boolean; pcase: any }>({ open: false, pcase: null })
  const [execStatus, setExecStatus] = useState('pass')
  const [execNotes, setExecNotes] = useState('')
  const [execSaving, setExecSaving] = useState(false)
  const [executions, setExecutions] = useState<any>({ total: 0, items: [] })
  const [execLoading, setExecLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deletePlanOpen, setDeletePlanOpen] = useState(false)
  const [autoExecuting, setAutoExecuting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d: any = await fetchPlan(planId)
      setPlan(d)
    } finally { setLoading(false) }
  }, [planId])

  const loadExecutions = useCallback(async () => {
    setExecLoading(true)
    try {
      const d: any = await fetchExecutions(planId)
      setExecutions(d)
    } finally { setExecLoading(false) }
  }, [planId])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadExecutions() }, [loadExecutions])

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

  const doRemoveCase = async (caseId: number) => {
    await removeCasesFromPlan(planId, [caseId])
    toast.success('已移除')
    setDeleteTarget(null)
    load()
  }

  const doAutoExecute = async () => {
    setAutoExecuting(true)
    try {
      const result: any = await autoExecutePlan(planId)
      toast.success(`批量执行完成: ${result.executed} 条执行, ${result.passed} 通过, ${result.failed} 失败`)
      load()
      loadExecutions()
    } catch (e: any) {
      toast.error(e?.message || '批量执行失败')
    } finally { setAutoExecuting(false) }
  }

  const doExecute = async () => {
    if (!execModal.pcase) return
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
    setExecStatus('pass')
    setExecNotes('')
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
        {plan.plan_id && <Badge variant="outline">{plan.plan_id}</Badge>}
        <Badge variant={PLAN_STATUS[plan.status]?.variant || 'outline'}>
          {PLAN_STATUS[plan.status]?.label || plan.status}
        </Badge>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="default"
            onClick={doAutoExecute}
            disabled={autoExecuting || !plan.cases?.length}
          >
            <Play className="size-3.5" data-icon="inline-start" />
            {autoExecuting ? '执行中...' : '批量执行'}
          </Button>
          {plan.status === 'draft' && (
            <Button size="sm" onClick={() => doUpdateStatus('active')}>开始执行</Button>
          )}
          {plan.status === 'active' && (
            <Button size="sm" onClick={() => doUpdateStatus('completed')}>标记完成</Button>
          )}
          <Button size="sm" variant="outline" onClick={load}>
            <RotateCcw className="size-3.5" data-icon="inline-start" />
          </Button>
          <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>编辑</Button>
          <AlertDialog open={deletePlanOpen} onOpenChange={setDeletePlanOpen}>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="destructive">删除</Button>
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
                key === 'pass' && 'text-green-600',
                key === 'fail' && 'text-destructive',
                key === 'skip' && 'text-orange-500'
              )}>
                {val as number}
              </div>
              <div className="text-xs text-muted-foreground">{key}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Description (Descriptions) */}
      {plan.description && (
        <Card size="sm">
          <CardContent className="pt-[var(--card-spacing)]">
            <dl className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">描述</dt>
                <dd className="mt-0.5">{plan.description}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">开始</dt>
                <dd className="mt-0.5">{plan.start_date ? new Date(plan.start_date).toLocaleDateString() : '-'}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">结束</dt>
                <dd className="mt-0.5">{plan.end_date ? new Date(plan.end_date).toLocaleDateString() : '-'}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}

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
                        <TableCell colSpan={5} className="py-8">
                          <SkeletonText lines={4} />
                        </TableCell>
                      </TableRow>
                    ) : (plan.cases || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8">
                          <EmptyState title="暂无用例" description="点击「添加用例」将用例纳入计划" className="py-0" />
                        </TableCell>
                      </TableRow>
                    ) : (
                      (plan.cases || []).map((r: any) => {
                        const sc = STATUS_COLORS[r.last_status] || { variant: 'outline' as const }
                        return (
                          <TableRow key={r.id}>
                            <TableCell className="text-muted-foreground">{r.sort_order}</TableCell>
                            <TableCell className="max-w-0 truncate">
                              <div className="flex items-center gap-1">
                                <Badge variant={r.priority === 'P0' ? 'destructive' : r.priority === 'P1' ? 'secondary' : 'default'}>
                                  {r.priority}
                                </Badge>
                                {r.case_type === 'api' && (
                                  <Badge variant="secondary" className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                                    接口
                                  </Badge>
                                )}
                                <span className="text-xs text-muted-foreground mr-1">{r.case_id_code}</span>
                                <span className="truncate">{r.case_title}</span>
                              </div>
                            </TableCell>
                            <TableCell className="max-w-[100px] truncate">{r.module}</TableCell>
                            <TableCell>
                              <Badge variant={sc.variant} className={sc.className}>
                                {STATUS_ICONS[r.last_status]}
                                <span className="ml-0.5">{r.last_status || '-'}</span>
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
                                    <Button size="icon-xs" variant="ghost" className="text-destructive hover:bg-destructive/10" onClick={() => setDeleteTarget(r.case_id)}>
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
                      <TableHead className="w-[170px]">时间</TableHead>
                      <TableHead className="w-[80px]">链路</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {execLoading ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8">
                          <SkeletonText lines={4} />
                        </TableCell>
                      </TableRow>
                    ) : executions.items?.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8">
                          <EmptyState title="暂无执行记录" description="对用例执行测试后将在此显示记录" className="py-0" />
                        </TableCell>
                      </TableRow>
                    ) : (
                      (executions.items || []).map((r: any) => {
                        const sc = STATUS_COLORS[r.status] || { variant: 'outline' as const }
                        return (
                          <TableRow key={r.id}>
                            <TableCell className="max-w-0 truncate">{r.case_title}</TableCell>
                            <TableCell>
                              <Badge variant={sc.variant} className={sc.className}>{r.status}</Badge>
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">{r.notes || '-'}</TableCell>
                            <TableCell className="text-muted-foreground">
                              {r.executed_at ? new Date(r.executed_at).toLocaleString() : '-'}
                            </TableCell>
                            <TableCell>
                              {r.kibana_link ? (
                                <a href={r.kibana_link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline text-xs">
                                  <Link2 className="size-3" />
                                  Kibana
                                </a>
                              ) : r.trace_id ? (
                                <Badge variant="outline">{r.trace_id}</Badge>
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
            <Button variant="outline" onClick={() => setExecModal({ open: false, pcase: null })}>取消</Button>
            <Button disabled={execSaving} onClick={doExecute}>
              {execSaving ? '保存中...' : '确认'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
