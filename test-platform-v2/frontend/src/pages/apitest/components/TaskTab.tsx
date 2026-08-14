import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { RefreshCw, XCircle, CheckCircle2, Clock, Loader2, Eye, ChevronDown, ChevronRight, ClipboardCheck, Trash2, RotateCcw } from '@/lib/icons'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchApiExecutionTasks, fetchApiExecutionTask, cancelApiExecutionTask, retryApiExecutionTask, deleteApiExecutionTask } from '@/api/apitest'
import type { ApiExecutionTask, ApiTaskDetail } from '@/types'
import { execStatusLabel, normalizeExecStatus } from '@/utils/executionStatus'

const STATUS_CLASS: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground',
  running: 'bg-status-info-muted text-status-info',
  passed: 'bg-status-success-muted text-status-success',
  failed: 'bg-status-danger-muted text-status-danger',
  cancelled: 'bg-status-warning-muted text-status-warning',
}

/** 旧值 → 规范值兼容映射（后端已迁移，兼容历史数据） */
const STATUS_TONE_BY_NORMALIZED: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground',
  running: 'bg-status-info-muted text-status-info',
  passed: 'bg-status-success-muted text-status-success',
  failed: 'bg-status-danger-muted text-status-danger',
  cancelled: 'bg-status-warning-muted text-status-warning',
  skipped: 'bg-status-warning-muted text-status-warning',
  blocked: 'bg-status-danger-muted text-status-danger',
}

function statusBadgeClass(status?: string): string {
  return STATUS_TONE_BY_NORMALIZED[normalizeExecStatus(status)] ?? 'bg-muted text-muted-foreground'
}

export default function TaskTab() {
  const [tasks, setTasks] = useState<ApiExecutionTask[]>([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [detail, setDetail] = useState<ApiTaskDetail | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ApiExecutionTask | null>(null)

  const loadTasks = useCallback(async () => {
    try {
      const result = await fetchApiExecutionTasks({
        status: statusFilter || undefined,
        page_size: 20,
      })
      setTasks(result.items)
      setTotal(result.total)
    } catch { setTasks([]) }
  }, [statusFilter])

  useEffect(() => { loadTasks() }, [loadTasks])

  const viewDetail = async (taskId: number) => {
    try {
      const d = await fetchApiExecutionTask(taskId)
      setDetail(d)
      setDetailOpen(true)
    } catch (e: any) { toast.error(e?.message || '获取详情失败') }
  }

  const cancelTask = async (taskId: number) => {
    try {
      await cancelApiExecutionTask(taskId)
      toast.success('任务已取消')
      loadTasks()
    } catch (e: any) { toast.error(e?.message || '取消失败') }
  }

  const retryTask = async (taskId: number) => {
    try {
      await retryApiExecutionTask(taskId)
      toast.success('已创建重跑任务')
      loadTasks()
    } catch (e: any) { toast.error(e?.message || '重跑失败') }
  }

  const doDeleteTask = async () => {
    if (!deleteTarget) return
    try {
      await deleteApiExecutionTask(deleteTarget.id)
      toast.success('任务已删除')
      setDeleteTarget(null)
      loadTasks()
    } catch (e: any) { toast.error(e?.message || '删除失败') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select value={statusFilter || '_all'} onValueChange={v => setStatusFilter(v === '_all' ? '' : v)}>
          <SelectTrigger className="w-[150px]" aria-label="任务状态筛选"><SelectValue placeholder="全部状态" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">全部状态</SelectItem>
            <SelectItem value="running">执行中</SelectItem>
            <SelectItem value="success">成功</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
            <SelectItem value="cancelled">已取消</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="secondary" onClick={loadTasks} data-icon="inline-start" aria-label="刷新执行任务"><RefreshCw className="size-4" /></Button>
        <span className="text-xs text-muted-foreground">{total} 个任务</span>
      </div>

      <div className="border rounded-lg divide-y">
        {tasks.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground">
            <p className="text-sm">暂无执行任务</p>
            <p className="text-xs mt-1">在「接口用例」中选择用例发起批量执行</p>
          </div>
        ) : (
          tasks.map(task => (
            <div key={task.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50">
              <div className="shrink-0">
                {task.status === 'success' ? <CheckCircle2 className="size-5 text-status-success" />
                  : task.status === 'failed' ? <XCircle className="size-5 text-status-danger" />
                  : task.status === 'running' ? <Loader2 className="size-5 text-status-info animate-spin" />
                  : task.status === 'cancelled' ? <XCircle className="size-5 text-status-warning" />
                  : <Clock className="size-5 text-muted-foreground" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{task.name}</p>
                <p className="text-xs text-muted-foreground">{task.task_id} · {task.trigger_type}</p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-status-success">{task.passed} 通过</span>
                <span className="text-status-danger">{task.failed} 失败</span>
                {task.skipped > 0 && <span className="text-muted-foreground">{task.skipped} 跳过</span>}
              </div>
              <Badge className={statusBadgeClass(task.status)}>{execStatusLabel(task.status)}</Badge>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  size="icon-sm"
                  variant="ghost"
                  onClick={() => viewDetail(task.id)}
                  aria-label={`查看任务${task.name}详情`}
                >
                  <Eye className="size-4" />
                </Button>
                {(task.status === 'pending' || task.status === 'running') && (
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => cancelTask(task.id)}
                    aria-label={`取消任务${task.name}`}
                  >
                    <XCircle className="size-4" />
                  </Button>
                )}
                {task.failed > 0 && task.status !== 'pending' && task.status !== 'running' && (
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={() => retryTask(task.id)}
                    aria-label={`重跑失败用例：${task.name}`}
                    title="重跑失败用例"
                  >
                    <RotateCcw className="size-4" />
                  </Button>
                )}
                {task.status !== 'pending' && task.status !== 'running' && (
                  <AlertDialog open={deleteTarget?.id === task.id} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
                    <AlertDialogTrigger asChild>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => setDeleteTarget(task)}
                        aria-label={`删除任务${task.name}`}
                        title="删除任务"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent size="sm">
                      <AlertDialogHeader>
                        <AlertDialogTitle>确定删除执行任务？</AlertDialogTitle>
                        <AlertDialogDescription>将同时删除任务下所有执行明细，此操作无法撤销。</AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>取消</AlertDialogCancel>
                        <AlertDialogAction variant="destructive" onClick={() => void doDeleteTask()}>删除</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Detail side panel */}
      {detailOpen && detail && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">{detail.name}</CardTitle>
            <Button size="sm" variant="ghost" onClick={() => setDetailOpen(false)}>关闭</Button>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-3 mb-4 text-center">
              <div className="bg-muted rounded p-2"><div className="text-lg font-bold">{detail.total}</div><div className="text-xs text-muted-foreground">总数</div></div>
              <div className="bg-status-success-muted rounded p-2"><div className="text-lg font-bold text-status-success">{detail.passed}</div><div className="text-xs text-muted-foreground">通过</div></div>
              <div className="bg-status-danger-muted rounded p-2"><div className="text-lg font-bold text-status-danger">{detail.failed}</div><div className="text-xs text-muted-foreground">失败</div></div>
              <div className="bg-muted rounded p-2"><div className="text-lg font-bold">{detail.skipped}</div><div className="text-xs text-muted-foreground">跳过</div></div>
            </div>
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {detail.items.map((item, i) => (
                <SnapshotCard key={item.id} item={item} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function safeFormatJson(raw: string): string {
  try { return JSON.stringify(JSON.parse(raw), null, 2) } catch { return raw }
}

function SnapshotCard({ item }: { item: { id: number; case_id: number; status: string; duration_ms: number; error_message: string; assertion_results: string; request_snapshot: string; response_snapshot: string; test_execution_id?: number | null } }) {
  const [expanded, setExpanded] = useState(false)
  const [tab, setTab] = useState<'request' | 'response' | 'assertions'>('request')

  const reqSnap = parseSnapshot(item.request_snapshot)
  const resSnap = parseSnapshot(item.response_snapshot)

  return (
    <div className="border rounded p-3 text-xs">
      <div className="flex items-center gap-2 mb-1">
        <Button size="icon-xs" variant="ghost" onClick={() => setExpanded(!expanded)} aria-label={expanded ? '收起' : '展开'}>
          {expanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        </Button>
        {item.status === 'passed' ? <CheckCircle2 className="size-3 text-status-success" /> : <XCircle className="size-3 text-status-danger" />}
        <span className="font-medium">用例 #{item.case_id}</span>
        <span className="text-muted-foreground">{item.duration_ms}ms</span>
        <Badge className={statusBadgeClass(item.status)}>{execStatusLabel(item.status)}</Badge>
        {item.test_execution_id ? <span className="text-muted-foreground">关联计划执行 #{item.test_execution_id}</span> : null}
      </div>
      {item.error_message && <p className="text-status-danger mt-1">{item.error_message}</p>}

      {expanded && (
        <div className="mt-2 border-t pt-2">
          <div className="flex items-center gap-1 mb-2">
            {(['request', 'response', 'assertions'] as const).map(t => (
              <Button key={t} size="xs" variant={tab === t ? 'primary' : 'ghost'} onClick={() => setTab(t)}>
                {t === 'request' ? '请求' : t === 'response' ? '响应' : '断言'}
              </Button>
            ))}
          </div>
          {tab === 'request' && (
            <div className="space-y-1">
              {reqSnap ? (
                <>
                  <div className="flex items-center gap-2">
                    <Badge tone="neutral">{reqSnap.method || 'GET'}</Badge>
                    <span className="font-mono text-xs truncate max-w-[300px]" title={reqSnap.url || reqSnap.resolved_url || '-'}>{reqSnap.url || reqSnap.resolved_url || '-'}</span>
                    <Button
                      size="icon-xs"
                      variant="ghost"
                      onClick={() => { navigator.clipboard.writeText(reqSnap.curl || ''); toast.success('curl 已复制') }}
                      aria-label="复制 curl"
                      title="复制 curl"
                    >
                      <ClipboardCheck className="size-3" />
                    </Button>
                  </div>
                  {reqSnap.headers && Object.keys(reqSnap.headers).length > 0 && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">请求头 ({Object.keys(reqSnap.headers).length})</summary>
                      <pre className="text-xs bg-muted p-1 rounded mt-0.5 max-h-20 overflow-auto">{safeFormatJson(JSON.stringify(reqSnap.headers))}</pre>
                    </details>
                  )}
                  {reqSnap.body && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">请求体</summary>
                      <pre className="text-xs bg-muted p-1 rounded mt-0.5 max-h-32 overflow-auto">{safeFormatJson(reqSnap.body)}</pre>
                    </details>
                  )}
                </>
              ) : <span className="text-muted-foreground">无请求快照</span>}
            </div>
          )}
          {tab === 'response' && (
            <div className="space-y-1">
              {resSnap ? (
                <>
                  <div className="flex items-center gap-2">
                    <Badge tone={resSnap.status_code >= 400 ? 'danger' : 'success'}>{resSnap.status_code || '-'}</Badge>
                    <span className="text-muted-foreground">{resSnap.body_size_bytes != null ? `${(resSnap.body_size_bytes / 1024).toFixed(1)} KB` : ''}</span>
                    {resSnap.truncated && <Badge tone="neutral">已截断</Badge>}
                  </div>
                  {resSnap.headers && Object.keys(resSnap.headers).length > 0 && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">响应头 ({Object.keys(resSnap.headers).length})</summary>
                      <pre className="text-xs bg-muted p-1 rounded mt-0.5 max-h-20 overflow-auto">{safeFormatJson(JSON.stringify(resSnap.headers))}</pre>
                    </details>
                  )}
                  {resSnap.body_preview && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">响应体预览{resSnap.truncated ? ' (已截断)' : ''}</summary>
                      <pre className="text-xs bg-muted p-1 rounded mt-0.5 max-h-48 overflow-auto">{formatBodyPreview(resSnap.body_preview, resSnap.content_type)}</pre>
                    </details>
                  )}
                </>
              ) : <span className="text-muted-foreground">无响应快照</span>}
            </div>
          )}
          {tab === 'assertions' && (
            item.assertion_results && item.assertion_results !== '[]' ? (
              <div>
                <pre className="text-xs bg-muted p-1 rounded mt-0.5 max-h-32 overflow-auto">{safeFormatJson(item.assertion_results)}</pre>
              </div>
            ) : <span className="text-muted-foreground">无断言结果</span>
          )}
        </div>
      )}
    </div>
  )
}

function parseSnapshot(raw: string): Record<string, any> | null {
  if (!raw || raw === '{}' || raw === 'null') return null
  try { return JSON.parse(raw) } catch { return null }
}

function formatBodyPreview(body: string, contentType: string): string {
  if (!body) return '(空)'
  if (contentType?.includes('json') || body.trim().startsWith('{') || body.trim().startsWith('[')) {
    try { return JSON.stringify(JSON.parse(body), null, 2) } catch { return body }
  }
  return body
}
