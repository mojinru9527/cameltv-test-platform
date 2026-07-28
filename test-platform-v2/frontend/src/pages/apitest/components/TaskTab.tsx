import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { RefreshCw, XCircle, CheckCircle2, Clock, Loader2, Eye, ChevronDown, ChevronRight, ClipboardCheck } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchApiExecutionTasks, fetchApiExecutionTask, cancelApiExecutionTask } from '@/api/apitest'
import type { ApiExecutionTask, ApiTaskDetail } from '@/types'

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending: { label: '待执行', className: 'bg-gray-100 text-gray-700' },
  running: { label: '执行中', className: 'bg-blue-100 text-blue-700' },
  success: { label: '成功', className: 'bg-green-100 text-green-700' },
  failed: { label: '失败', className: 'bg-red-100 text-red-700' },
  cancelled: { label: '已取消', className: 'bg-yellow-100 text-yellow-700' },
}

export default function TaskTab() {
  const [tasks, setTasks] = useState<ApiExecutionTask[]>([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [detail, setDetail] = useState<ApiTaskDetail | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

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

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select value={statusFilter || '_all'} onValueChange={v => setStatusFilter(v === '_all' ? '' : v)}>
          <SelectTrigger className="w-[150px]"><SelectValue placeholder="全部状态" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">全部状态</SelectItem>
            <SelectItem value="running">执行中</SelectItem>
            <SelectItem value="success">成功</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
            <SelectItem value="cancelled">已取消</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={loadTasks} data-icon="inline-start"><RefreshCw className="size-4" /></Button>
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
                {task.status === 'success' ? <CheckCircle2 className="size-5 text-green-600" />
                  : task.status === 'failed' ? <XCircle className="size-5 text-red-600" />
                  : task.status === 'running' ? <Loader2 className="size-5 text-blue-600 animate-spin" />
                  : task.status === 'cancelled' ? <XCircle className="size-5 text-yellow-600" />
                  : <Clock className="size-5 text-gray-400" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{task.name}</p>
                <p className="text-xs text-muted-foreground">{task.task_id} · {task.trigger_type}</p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-green-600">{task.passed} 通过</span>
                <span className="text-red-600">{task.failed} 失败</span>
                {task.skipped > 0 && <span className="text-muted-foreground">{task.skipped} 跳过</span>}
              </div>
              <Badge className={STATUS_MAP[task.status]?.className || ''}>{STATUS_MAP[task.status]?.label || task.status}</Badge>
              <div className="flex items-center gap-1 shrink-0">
                <Button size="icon-sm" variant="ghost" onClick={() => viewDetail(task.id)}><Eye className="size-4" /></Button>
                {(task.status === 'pending' || task.status === 'running') && (
                  <Button size="icon-sm" variant="ghost" className="text-destructive" onClick={() => cancelTask(task.id)}>
                    <XCircle className="size-4" />
                  </Button>
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
              <div className="bg-green-50 rounded p-2"><div className="text-lg font-bold text-green-600">{detail.passed}</div><div className="text-xs text-muted-foreground">通过</div></div>
              <div className="bg-red-50 rounded p-2"><div className="text-lg font-bold text-red-600">{detail.failed}</div><div className="text-xs text-muted-foreground">失败</div></div>
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

function SnapshotCard({ item }: { item: { id: number; case_id: number; status: string; duration_ms: number; error_message: string; assertion_results: string; request_snapshot: string; response_snapshot: string } }) {
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
        {item.status === 'passed' ? <CheckCircle2 className="size-3 text-green-600" /> : <XCircle className="size-3 text-red-600" />}
        <span className="font-medium">用例 #{item.case_id}</span>
        <span className="text-muted-foreground">{item.duration_ms}ms</span>
        <Badge className={STATUS_MAP[item.status]?.className || ''}>{STATUS_MAP[item.status]?.label || item.status}</Badge>
      </div>
      {item.error_message && <p className="text-red-600 mt-1">{item.error_message}</p>}

      {expanded && (
        <div className="mt-2 border-t pt-2">
          <div className="flex items-center gap-1 mb-2">
            {(['request', 'response', 'assertions'] as const).map(t => (
              <Button key={t} size="xs" variant={tab === t ? 'default' : 'ghost'} onClick={() => setTab(t)}>
                {t === 'request' ? '请求' : t === 'response' ? '响应' : '断言'}
              </Button>
            ))}
          </div>
          {tab === 'request' && (
            <div className="space-y-1">
              {reqSnap ? (
                <>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{reqSnap.method || 'GET'}</Badge>
                    <span className="font-mono text-[10px] truncate max-w-[300px]">{reqSnap.url || reqSnap.resolved_url || '-'}</span>
                    <Button size="icon-xs" variant="ghost" onClick={() => { navigator.clipboard.writeText(reqSnap.curl || ''); toast.success('curl 已复制') }} title="复制 curl">
                      <ClipboardCheck className="size-3" />
                    </Button>
                  </div>
                  {reqSnap.headers && Object.keys(reqSnap.headers).length > 0 && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">请求头 ({Object.keys(reqSnap.headers).length})</summary>
                      <pre className="text-[10px] bg-muted p-1 rounded mt-0.5 max-h-20 overflow-auto">{safeFormatJson(JSON.stringify(reqSnap.headers))}</pre>
                    </details>
                  )}
                  {reqSnap.body && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">请求体</summary>
                      <pre className="text-[10px] bg-muted p-1 rounded mt-0.5 max-h-32 overflow-auto">{safeFormatJson(reqSnap.body)}</pre>
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
                    <Badge variant={resSnap.status_code >= 400 ? 'destructive' : 'default'}>{resSnap.status_code || '-'}</Badge>
                    <span className="text-muted-foreground">{resSnap.body_size_bytes != null ? `${(resSnap.body_size_bytes / 1024).toFixed(1)} KB` : ''}</span>
                    {resSnap.truncated && <Badge variant="outline">已截断</Badge>}
                  </div>
                  {resSnap.headers && Object.keys(resSnap.headers).length > 0 && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">响应头 ({Object.keys(resSnap.headers).length})</summary>
                      <pre className="text-[10px] bg-muted p-1 rounded mt-0.5 max-h-20 overflow-auto">{safeFormatJson(JSON.stringify(resSnap.headers))}</pre>
                    </details>
                  )}
                  {resSnap.body_preview && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted-foreground">响应体预览{resSnap.truncated ? ' (已截断)' : ''}</summary>
                      <pre className="text-[10px] bg-muted p-1 rounded mt-0.5 max-h-48 overflow-auto">{formatBodyPreview(resSnap.body_preview, resSnap.content_type)}</pre>
                    </details>
                  )}
                </>
              ) : <span className="text-muted-foreground">无响应快照</span>}
            </div>
          )}
          {tab === 'assertions' && (
            item.assertion_results && item.assertion_results !== '[]' ? (
              <div>
                <pre className="text-[10px] bg-muted p-1 rounded mt-0.5 max-h-32 overflow-auto">{safeFormatJson(item.assertion_results)}</pre>
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
