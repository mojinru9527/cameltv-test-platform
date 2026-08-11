import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Play, ClipboardCheck, MinusCircle, Loader2, CheckCircle2, XCircle, RefreshCw, ChevronDown } from '@/lib/icons'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import ProductionOperationDialog from '@/components/ProductionOperationDialog'
import { fetchTestCases } from '@/api/testcase'
import { executeApiCase, createApiExecutionTask } from '@/api/apitest'
import { fetchEnvironments } from '@/api/environment'
import { fetchDatasets } from '@/api/dataset'
import { useAuthStore } from '@/stores/auth'
import { ResponsePanel } from './DebugTab'
import { groupApiCases } from './apiCaseGroups'
import { buildApiExecutionRequest, type ApiExecutionSource } from '../apiExecutionRequest'
import type { ApiExecutionResult, BatchExecutionResult, ApiAssertionResult, Environment } from '@/types'

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-status-info-muted text-status-info', POST: 'bg-status-success-muted text-status-success',
  PUT: 'bg-status-warning-muted text-status-warning', PATCH: 'bg-status-accent-muted text-status-accent',
  DELETE: 'bg-status-danger-muted text-status-danger',
}

function isBatchResult(res: ApiExecutionResult | BatchExecutionResult): res is BatchExecutionResult {
  return 'batch_mode' in res && (res as any).batch_mode
}

export default function ApiCaseTab() {
  const projectId = useAuthStore(s => s.currentProjectId)
  const [apiCases, setApiCases] = useState<any[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [executingCase, setExecutingCase] = useState<number | null>(null)
  const [responseModalOpen, setResponseModalOpen] = useState(false)
  const [envs, setEnvs] = useState<Environment[]>([])
  const [envId, setEnvId] = useState<number | undefined>()
  const [datasets, setDatasets] = useState<any[]>([])
  const [datasetId, setDatasetId] = useState<number | undefined>()
  const [pendingExecution, setPendingExecution] = useState<{
    source: Extract<ApiExecutionSource, 'single' | 'group' | 'batch'>
    cases: any[]
    name: string
  } | null>(null)
  const executionInFlightRef = useRef(false)

  function isProductionEnv(env: Environment): boolean {
    return env.is_production === true || env.env_type === 'prod'
  }

  const loadCases = useCallback(async (signal?: AbortSignal) => {
    try {
      const data: any = await fetchTestCases({ case_type: 'api', page_size: 100 }, signal)
      setApiCases(data?.items || [])
    } catch (loadError: any) {
      if (signal?.aborted) return
      setApiCases([])
      toast.error(loadError?.message || '接口用例加载失败')
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadCases(controller.signal)
    return () => controller.abort()
  }, [loadCases])

  useEffect(() => {
    const controller = new AbortController()
    fetchEnvironments(controller.signal).then(setEnvs).catch((loadError: any) => {
      if (controller.signal.aborted) return
      toast.error(loadError?.message || '环境列表加载失败')
    })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchDatasets({ page_size: 100 }).then((d: any) => setDatasets(d?.items || [])).catch(() => {})
    return () => controller.abort()
  }, [])

  const toggleSelect = (id: number) => {
    setSelected(prev => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next })
  }

  const toggleAll = () => {
    if (selected.size === apiCases.length) setSelected(new Set())
    else setSelected(new Set(apiCases.map(c => c.id)))
  }

  const toggleGroup = (groupCases: any[]) => {
    const ids = groupCases.map(c => c.id)
    const allSelected = ids.every(id => selected.has(id))
    setSelected(prev => {
      const next = new Set(prev)
      if (allSelected) { ids.forEach(id => next.delete(id)) }
      else { ids.forEach(id => next.add(id)) }
      return next
    })
  }

  const submitExecution = async (
    operation: NonNullable<typeof pendingExecution>,
    confirmProd: boolean,
  ) => {
    if (executionInFlightRef.current) return
    executionInFlightRef.current = true
    const caseIds = operation.cases.map(testCase => testCase.id)
    if (operation.source === 'single') setExecutingCase(caseIds[0])
    else setLoading(true)
    try {
      const request = buildApiExecutionRequest({
        source: operation.source,
        environmentId: envId,
        datasetId,
        caseIds,
        request: null,
        confirmProd,
      })
      if (operation.source === 'single') {
        setResult(null)
        const res = await executeApiCase(request)
        setResult(res as any)
        setResponseModalOpen(true)
        if (!isBatchResult(res) && res.all_pass) toast.success('全部断言通过')
        else if (!isBatchResult(res)) toast.error(`${res.assertions?.filter((a: ApiAssertionResult) => !a.passed).length || 0} 个断言失败`)
        return
      }

      const task = await createApiExecutionTask({ ...request, name: operation.name })
      toast.success(`${operation.source === 'group' ? '分组' : '批量'}任务已创建: ${task.task_id}，共 ${task.total} 条用例`)
      setTimeout(() => loadCases(), 1000)
    } catch (e: any) {
      toast.error(e?.message || '执行失败')
      if (operation.source === 'single') {
        setResult({ error: true, message: e?.message || '网络请求失败，请检查后端服务是否启动' })
        setResponseModalOpen(true)
      }
    } finally {
      executionInFlightRef.current = false
      setExecutingCase(null)
      setLoading(false)
    }
  }

  const requestExecution = (
    source: Extract<ApiExecutionSource, 'single' | 'group' | 'batch'>,
    cases: any[],
    name: string,
  ) => {
    if (!projectId) { toast.error('未选择项目'); return }
    if (cases.length === 0) { toast.error('请至少选择一条用例'); return }
    const operation = { source, cases, name }
    const selectedEnv = envs.find(e => e.id === envId)
    const hasWrite = cases.some(testCase => !['GET', 'HEAD', 'OPTIONS'].includes((testCase.api_method || 'GET').toUpperCase()))
    if (selectedEnv && isProductionEnv(selectedEnv) && hasWrite) {
      setPendingExecution(operation)
      return
    }
    void submitExecution(operation, false)
  }

  const runSingle = (caseId: number) => {
    const testCase = apiCases.find(item => item.id === caseId)
    if (!testCase) return
    requestExecution('single', [testCase], `单用例执行 ${testCase.title}`)
  }

  const runGroup = (groupCases: any[]) => {
    requestExecution(
      'group',
      groupCases,
      `分组执行 ${groupCases[0]?.api_endpoint || new Date().toLocaleString('zh-CN')}`,
    )
  }

  const runBatch = () => {
    const selectedCases = apiCases.filter(testCase => selected.has(testCase.id))
    requestExecution('batch', selectedCases, `批量执行 ${new Date().toLocaleString('zh-CN')}`)
  }

  const groups = groupApiCases(apiCases)

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={toggleAll} data-icon="inline-start">
            {selected.size === apiCases.length && apiCases.length > 0 ? <ClipboardCheck className="size-4" /> : <MinusCircle className="size-4" />}
            {selected.size > 0 ? `已选 ${selected.size}` : '全选'}
          </Button>
          <Button size="sm" onClick={runBatch} disabled={loading || selected.size === 0} data-icon="inline-start">
            {loading ? <Loader2 className="animate-spin size-4" /> : <Play className="size-4" />}
            批量执行 ({selected.size})
          </Button>
          {envs.length > 0 && (
            <Select value={envId?.toString() || '_none'} onValueChange={(v) => setEnvId(v === '_none' ? undefined : Number(v))}>
              <SelectTrigger className="w-[180px] h-8 text-xs"><SelectValue placeholder="不使用环境" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">不使用环境</SelectItem>
                {envs.map((e) => (
                  <SelectItem key={e.id} value={e.id.toString()}>{e.name} ({e.env_type})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {datasets.length > 0 && (
            <Select value={datasetId?.toString() || '_none'} onValueChange={(v) => setDatasetId(v === '_none' ? undefined : Number(v))}>
              <SelectTrigger className="w-[180px] h-8 text-xs" aria-label="按数据集执行"><SelectValue placeholder="不使用数据集" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">不使用数据集（用例默认）</SelectItem>
                {datasets.map((d: any) => (
                  <SelectItem key={d.id} value={d.id.toString()}>{d.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
        <span className="text-xs text-muted-foreground">{apiCases.length} 条</span>
      </div>

      {/* Grouped case list */}
      <div className="border rounded-lg max-h-[70vh] overflow-y-auto">
        {apiCases.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground">
            <p className="text-sm">暂无 API 用例</p>
            <p className="text-xs mt-1">在「接口资产」中导入接口并生成用例</p>
          </div>
        ) : (
          <div className="divide-y">
            {groups.map((group) => {
              const groupAllSelected = group.cases.length > 0 && group.cases.every((c: any) => selected.has(c.id))
              return (
                <Collapsible key={group.key} defaultOpen={false}>
                  <div className="flex items-center gap-2 px-4 py-3 hover:bg-muted/50">
                    <button
                      type="button"
                      onClick={() => toggleGroup(group.cases)}
                      className="shrink-0"
                      aria-label={groupAllSelected ? `取消选择 ${group.endpoint} 分组` : `选择 ${group.endpoint} 分组`}
                    >
                      {groupAllSelected
                        ? <ClipboardCheck className="size-4 text-primary" />
                        : <MinusCircle className="size-4 text-muted-foreground" />
                      }
                    </button>
                    <CollapsibleTrigger className="flex min-w-0 flex-1 items-center justify-between gap-2 text-left">
                      <div className="flex min-w-0 items-center gap-2">
                      <ChevronDown className="size-4 transition-transform duration-200 collapsible-chevron group-data-[state=open]:rotate-180" />
                      <Badge className={METHOD_COLORS[group.method] || ''}>{group.method}</Badge>
                        <code className="truncate text-sm font-medium">{group.endpoint}</code>
                      </div>
                      <Badge tone="neutral" className="text-xs">{group.cases.length} 条用例</Badge>
                    </CollapsibleTrigger>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => runGroup(group.cases)}
                      disabled={loading}
                      data-icon="inline-start"
                    >
                      <Play className="size-3.5" />
                      执行全部
                    </Button>
                  </div>
                  <CollapsibleContent>
                    <div className="divide-y border-t">
                      {group.cases.map((c: any) => (
                        <div
                          key={c.id}
                          className={`flex items-center gap-3 px-4 py-3 hover:bg-muted/50 ${selected.has(c.id) ? 'bg-muted/30' : ''}`}
                        >
                          <button
                            type="button"
                            onClick={() => toggleSelect(c.id)}
                            className="shrink-0 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`${selected.has(c.id) ? '取消选择' : '选择'}用例${c.title}`}
                            aria-pressed={selected.has(c.id)}
                          >
                            {selected.has(c.id)
                              ? <ClipboardCheck className="size-4 text-primary" />
                              : <MinusCircle className="size-4 text-muted-foreground" />
                            }
                          </button>
                          <Badge className={METHOD_COLORS[c.api_method || 'GET'] || ''}>{c.api_method || 'GET'}</Badge>
                          <button
                            type="button"
                            className="min-w-0 flex-1 rounded-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            onClick={() => runSingle(c.id)}
                            aria-label={`执行用例${c.title}`}
                          >
                            <p className="text-sm font-medium truncate">{c.title}</p>
                            <p className="text-xs text-muted-foreground truncate">{c.api_endpoint}</p>
                          </button>
                          <div className="flex items-center gap-1 shrink-0">
                            <Badge tone="neutral" className="text-xs">{c.priority}</Badge>
                            <Button
                              size="icon-sm"
                              variant="ghost"
                              onClick={() => runSingle(c.id)}
                              disabled={executingCase === c.id}
                              aria-label={`执行用例${c.title}`}
                            >
                              {executingCase === c.id ? <Loader2 className="animate-spin size-4" /> : <Play className="size-4" />}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )
            })}
          </div>
        )}
      </div>

      {/* Response Modal */}
      <Dialog open={responseModalOpen} onOpenChange={setResponseModalOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>执行结果</DialogTitle>
          </DialogHeader>
          <ResponsePanel result={result} loading={false} />
        </DialogContent>
      </Dialog>

      <ProductionOperationDialog
        open={pendingExecution !== null}
        onOpenChange={(open) => { if (!open) setPendingExecution(null) }}
        project={`项目 #${projectId ?? '-'}`}
        environment={envs.find(environment => environment.id === envId)?.name ?? '未选择环境'}
        baseUrl={envs.find(environment => environment.id === envId)?.base_url ?? '未配置'}
        operation={pendingExecution?.name ?? '执行 API 用例'}
        classification="write"
        affectedCount={pendingExecution?.cases.length ?? 0}
        isProduction={true}
        pending={loading || executingCase !== null}
        onConfirm={() => {
          if (!pendingExecution) return
          const operation = pendingExecution
          setPendingExecution(null)
          return submitExecution(operation, true)
        }}
      />
    </div>
  )
}
