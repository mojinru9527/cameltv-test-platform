import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  fetchAgentRuns,
  fetchAgentTypes,
  triggerAgent,
  fetchAgentRun,
  type AgentRun,
  type AgentTypeMeta,
} from '@/api/agent'
import {
  Sparkles,
  FileText,
  GitBranch,
  TestTube2,
  Bug,
  Play,
  Loader2,
  RefreshCw,
  Clock,
} from '@/lib/icons'

const AGENT_ICONS: Record<string, React.ComponentType<any>> = {
  requirement_analysis: FileText,
  impact_analysis: GitBranch,
  case_generation: TestTube2,
  failure_analysis: Bug,
}
const AGENT_COLORS: Record<string, string> = {
  requirement_analysis: 'bg-purple-100 text-purple-700 border-purple-200',
  impact_analysis: 'bg-amber-100 text-amber-700 border-amber-200',
  case_generation: 'bg-blue-100 text-blue-700 border-blue-200',
  failure_analysis: 'bg-red-100 text-red-700 border-red-200',
}
const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'bg-muted text-muted-foreground' },
  running: { label: '执行中', color: 'bg-blue-100 text-blue-700' },
  success: { label: '成功', color: 'bg-green-100 text-green-700' },
  failed: { label: '失败', color: 'bg-red-100 text-red-700' },
  cancelled: { label: '已取消', color: 'bg-muted text-muted-foreground' },
}

export default function AgentWorkbenchPage() {
  useDocumentTitle('Agent 工作台')

  const [agentTypes, setAgentTypes] = useState<AgentTypeMeta[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [runsLoading, setRunsLoading] = useState(true)
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null)
  const [runDetail, setRunDetail] = useState<AgentRun | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Trigger dialog
  const [triggerDialog, setTriggerDialog] = useState<AgentTypeMeta | null>(null)
  const [triggerQuery, setTriggerQuery] = useState('')
  const [triggering, setTriggering] = useState(false)

  const loadRuns = useCallback(() => {
    setRunsLoading(true)
    fetchAgentRuns({ page_size: 50 })
      .then((res) => setRuns(res.items))
      .catch(() => toast.error('加载执行记录失败'))
      .finally(() => setRunsLoading(false))
  }, [])

  const loadTypes = useCallback(() => {
    fetchAgentTypes()
      .then(setAgentTypes)
      .catch(() => {})
  }, [])

  useEffect(() => {
    loadTypes()
    loadRuns()
  }, [loadTypes, loadRuns])

  // Load run detail when selected
  useEffect(() => {
    if (!selectedRun?.id) return
    setDetailLoading(true)
    fetchAgentRun(selectedRun.id)
      .then(setRunDetail)
      .catch(() => toast.error('加载详情失败'))
      .finally(() => setDetailLoading(false))
  }, [selectedRun?.id])

  const handleTrigger = async () => {
    if (!triggerDialog || !triggerQuery.trim()) return
    setTriggering(true)
    try {
      const result = await triggerAgent(triggerDialog.type, triggerQuery.trim())
      toast.success(result.message || 'Agent 已启动')
      setTriggerDialog(null)
      setTriggerQuery('')
      loadRuns()
    } catch (e: any) {
      toast.error(e?.message || '触发失败')
    } finally {
      setTriggering(false)
    }
  }

  const handleRefresh = () => loadRuns()

  // Parse JSON safely
  const safeJson = (s: string) => {
    try { return JSON.parse(s) } catch { return null }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Agent 工作台"
        description="触发 AI Agent 执行需求分析、影响评估、用例生成和失败分析。"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Agent 类型卡片 */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium">可用 Agent</h3>
          {agentTypes.length === 0 ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            agentTypes.map((t) => {
              const Icon = AGENT_ICONS[t.type] ?? Sparkles
              return (
                <Card key={t.type} className={`border-2 ${AGENT_COLORS[t.type]?.split(' ')[2] || 'border-border'}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${AGENT_COLORS[t.type] || 'bg-muted'}`}>
                        <Icon className="size-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-sm">{t.label}</h4>
                        <p className="text-xs text-muted-foreground mt-1">{t.description}</p>
                      </div>
                    </div>
                    <Button
                      className="w-full mt-3"
                      size="sm"
                      onClick={() => setTriggerDialog(t)}
                    >
                      <Play className="size-4 mr-1" />
                      执行
                    </Button>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>

        {/* 执行历史 */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">执行历史</h3>
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={runsLoading}>
              <RefreshCw className={`size-4 mr-1 ${runsLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">Agent</TableHead>
                    <TableHead className="w-40">输入</TableHead>
                    <TableHead className="w-20">状态</TableHead>
                    <TableHead className="w-20">耗时</TableHead>
                    <TableHead className="w-36">时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runsLoading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-28" /></TableCell>
                      </TableRow>
                    ))
                  ) : runs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        暂无执行记录。点击左侧 Agent 卡片「执行」按钮启动。
                      </TableCell>
                    </TableRow>
                  ) : (
                    runs.map((r) => {
                      const input = safeJson(r.input_json)
                      const status = STATUS_BADGE[r.status] ?? { label: r.status, color: '' }
                      return (
                        <TableRow
                          key={r.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => setSelectedRun(r)}
                        >
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {r.agent_type.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground truncate max-w-40">
                            {input?.query || input?.user_input || '-'}
                          </TableCell>
                          <TableCell>
                            <Badge className={status.color}>{status.label}</Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {r.duration_ms ? `${(r.duration_ms / 1000).toFixed(1)}s` : '-'}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {r.created_at?.slice(0, 19)?.replace('T', ' ') || '-'}
                          </TableCell>
                        </TableRow>
                      )
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 执行详情 Sheet */}
      <Sheet open={!!selectedRun} onOpenChange={(open) => { if (!open) { setSelectedRun(null); setRunDetail(null) } }}>
        <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Agent 执行详情</SheetTitle>
          </SheetHeader>
          {detailLoading ? (
            <div className="space-y-3 mt-6">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : runDetail ? (
            <div className="mt-6 space-y-4 text-sm">
              <div className="flex items-center gap-2">
                <Badge className={AGENT_COLORS[runDetail.agent_type] || ''}>
                  {runDetail.agent_type.replace(/_/g, ' ')}
                </Badge>
                <Badge className={STATUS_BADGE[runDetail.status]?.color}>
                  {STATUS_BADGE[runDetail.status]?.label}
                </Badge>
              </div>

              {runDetail.error_message && (
                <div className="rounded-md bg-red-50 border border-red-200 p-3">
                  <p className="text-red-700 text-xs font-mono">{runDetail.error_message}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div>耗时: {runDetail.duration_ms ? `${(runDetail.duration_ms / 1000).toFixed(1)}s` : '-'}</div>
                <div>触发: {runDetail.trigger_type}</div>
                <div>创建: {runDetail.created_at?.slice(0, 19)?.replace('T', ' ') || '-'}</div>
                <div>完成: {runDetail.finished_at?.slice(0, 19)?.replace('T', ' ') || '-'}</div>
              </div>

              {runDetail.input_json && (
                <div>
                  <h4 className="font-medium mb-1">输入参数</h4>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-32">
                    {JSON.stringify(safeJson(runDetail.input_json), null, 2)}
                  </pre>
                </div>
              )}

              {runDetail.output_json && runDetail.output_json !== '{}' && (
                <div>
                  <h4 className="font-medium mb-1">输出结果</h4>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-64">
                    {JSON.stringify(safeJson(runDetail.output_json), null, 2)}
                  </pre>
                </div>
              )}

              {runDetail.retrieved_context_json && runDetail.retrieved_context_json !== '{}' && (
                <div>
                  <h4 className="font-medium mb-1">检索上下文</h4>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-32">
                    {JSON.stringify(safeJson(runDetail.retrieved_context_json), null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : null}
        </SheetContent>
      </Sheet>

      {/* 触发 Dialog */}
      <Dialog open={!!triggerDialog} onOpenChange={(open) => { if (!open) setTriggerDialog(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>执行 {triggerDialog?.label}</DialogTitle>
            <DialogDescription>
              {triggerDialog?.description}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <Label>输入内容</Label>
            <Textarea
              placeholder="输入需求描述、API 地址、或缺陷信息…"
              value={triggerQuery}
              onChange={(e) => setTriggerQuery(e.target.value)}
              rows={5}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTriggerDialog(null)}>取消</Button>
            <Button onClick={handleTrigger} disabled={triggering || !triggerQuery.trim()}>
              {triggering ? (
                <>
                  <Loader2 className="size-4 mr-1 animate-spin" />
                  执行中…
                </>
              ) : (
                <>
                  <Play className="size-4 mr-1" />
                  开始执行
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
