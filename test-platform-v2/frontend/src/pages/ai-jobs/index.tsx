import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, Upload, Zap } from '@/lib/icons'
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsList,
  TabsTrigger,
  Badge as ToneBadge,
  StatusBadge,
} from '@/ui'
import {
  fetchAiAgentHealth,
  fetchAiJobs,
  importAiJobResult,
  type AiAgentHealthItem,
  type AiJobItem,
} from '@/api/aiAgent'

const STATUS_TABS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待认领' },
  { value: 'running', label: '执行中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
]

/** 平台 Job 状态 → 语义状态徽标（Batch 54 治理：禁止固定色板类）。 */
const STATUS_VARIANT: Record<string, 'pass' | 'fail' | 'running' | 'pending' | 'blocked' | 'skipped'> = {
  pending: 'pending',
  running: 'running',
  completed: 'pass',
  failed: 'fail',
  cancelled: 'skipped',
}

function extractError(err: unknown): string {
  const anyErr = err as {
    msg?: string
    detail?: string
    message?: string
    response?: { data?: Record<string, string> }
  }
  return (
    anyErr?.response?.data?.msg ||
    anyErr?.response?.data?.detail ||
    anyErr?.msg ||
    anyErr?.detail ||
    anyErr?.message ||
    '请求失败，请稍后重试'
  )
}

export default function AiJobsPage() {
  const [status, setStatus] = useState('all')
  const [jobs, setJobs] = useState<AiJobItem[]>([])
  const [agents, setAgents] = useState<AiAgentHealthItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<AiJobItem | null>(null)
  const [importing, setImporting] = useState(false)
  const [notice, setNotice] = useState('')

  const load = useCallback(
    async (signal?: AbortSignal, isCancelled?: () => boolean) => {
      setLoading(true)
      setError('')
      try {
        const [jobsRes, health] = await Promise.all([
          fetchAiJobs(
            { status: status === 'all' ? undefined : status, page: 1, page_size: 50 },
            signal,
          ),
          fetchAiAgentHealth(signal),
        ])
        if (isCancelled?.()) return
        setJobs(jobsRes.items)
        setAgents(health.items)
      } catch (err) {
        if (isCancelled?.()) return
        setError(extractError(err))
      } finally {
        if (!isCancelled?.()) setLoading(false)
      }
    },
    [status],
  )

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    void load(controller.signal, () => cancelled)
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [load])

  const handleImport = useCallback(async () => {
    if (!selected) return
    setImporting(true)
    setNotice('')
    try {
      const result = await importAiJobResult(selected.id)
      setNotice(
        result.already_imported
          ? `任务 #${selected.id} 此前已导入过，本次未重复写入用例。`
          : `已导入 ${result.imported} 条用例（跳过 ${result.skipped} 条）。`,
      )
      await load()
    } catch (err) {
      setNotice(extractError(err))
    } finally {
      setImporting(false)
    }
  }, [selected, load])

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">AI 任务</h1>
          <p className="text-sm text-muted-foreground">
            平台不执行 AI 推理：AI 任务在此派发给本地 Agent（本地 ChatGPT 客户端），平台只展示结果并导入用例库。
          </p>
        </div>
        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={loading ? 'mr-2 h-4 w-4 animate-spin' : 'mr-2 h-4 w-4'} />
          刷新
        </Button>
      </div>

      {notice && (
        <Alert>
          <AlertTitle>导入结果</AlertTitle>
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">任务列表</CardTitle>
            <Tabs value={status} onValueChange={setStatus}>
              <TabsList>
                {STATUS_TABS.map((tab) => (
                  <TabsTrigger key={tab.value} value={tab.value}>
                    {tab.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : error ? (
              <Alert variant="destructive">
                <AlertTitle>加载失败</AlertTitle>
                <AlertDescription className="flex items-center justify-between gap-3">
                  <span>{error}</span>
                  <Button variant="outline" size="sm" onClick={() => void load()}>
                    重试
                  </Button>
                </AlertDescription>
              </Alert>
            ) : jobs.length === 0 ? (
              <div className="space-y-1 py-8 text-center text-sm text-muted-foreground">
                <p>暂无 AI 任务。</p>
                <p>
                  这是预期状态：平台自己不跑 AI。请在需求页点击「AI 拆分 / AI 生成用例」，
                  再由本地 Agent 认领执行。
                </p>
                <p>
                  接入方式见 <code className="rounded bg-muted px-1">docs/ai/local-ai-agent.md</code>。
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">ID</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead>模型</TableHead>
                    <TableHead>创建时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow
                      key={job.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelected(job)}
                    >
                      <TableCell>#{job.id}</TableCell>
                      <TableCell>{job.job_type}</TableCell>
                      <TableCell>
                        <StatusBadge variant={STATUS_VARIANT[job.status] ?? 'pending'} label={job.status} />
                      </TableCell>
                      <TableCell className="text-muted-foreground">{job.agent_id || '—'}</TableCell>
                      <TableCell className="text-muted-foreground">{job.model_name || '—'}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {job.created_at?.replace('T', ' ').slice(0, 19) ?? '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4" /> 本地 Agent
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {agents.length === 0 ? (
              <p className="text-muted-foreground">本地 Agent 离线（暂无 Agent 上线认领任务）。</p>
            ) : (
              agents.map((agent) => (
                <div key={agent.agent_id} className="rounded-md border p-3">
                  <div className="font-medium">{agent.agent_id}</div>
                  <div className="text-xs">
                    <ToneBadge tone="success" className="mr-1">
                      在线
                    </ToneBadge>
                    scope={agent.project_scope}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    最近心跳：{agent.last_health_at?.replace('T', ' ').slice(0, 19) ?? '—'}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-[520px]">
          <SheetHeader>
            <SheetTitle>AI 任务 #{selected?.id}</SheetTitle>
            <SheetDescription>
              {selected?.job_type} · {selected?.status} · {selected?.model_name || '未上报模型'}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-4 space-y-4 text-sm">
            <div className="rounded-md border p-3">
              <div className="font-medium">任务输入</div>
              <pre className="mt-2 max-h-60 overflow-auto rounded bg-muted p-3 text-xs">
                {JSON.stringify(selected?.payload ?? {}, null, 2)}
              </pre>
            </div>
            {selected?.summary && (
              <div className="rounded-md border p-3">
                <div className="font-medium">结果摘要</div>
                <p className="mt-1 text-muted-foreground">{selected.summary}</p>
              </div>
            )}
            {selected?.error_message && (
              <Alert variant="destructive">
                <AlertTitle>失败原因</AlertTitle>
                <AlertDescription>{selected.error_message}</AlertDescription>
              </Alert>
            )}
            <Button
              className="w-full"
              disabled={
                selected?.status !== 'completed' || selected?.job_type !== 'generate' || importing
              }
              onClick={() => void handleImport()}
            >
              <Upload className="mr-2 h-4 w-4" />
              {importing ? '导入中…' : '导入用例库'}
            </Button>
            {selected && selected.job_type !== 'generate' && (
              <p className="text-xs text-muted-foreground">
                仅 generate 类型结果支持自动导入；extract 结果请在需求页人工确认。
              </p>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
