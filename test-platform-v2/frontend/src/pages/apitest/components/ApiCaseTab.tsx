import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Play, ClipboardCheck, MinusCircle, Loader2, CheckCircle2, XCircle, RefreshCw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { fetchTestCases } from '@/api/testcase'
import { executeApiCase, createApiExecutionTask } from '@/api/apitest'
import { useAuthStore } from '@/stores/auth'
import { ResponsePanel } from './DebugTab'
import type { ApiExecutionResult, BatchExecutionResult, ApiAssertionResult } from '@/types'

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-blue-100 text-blue-700', POST: 'bg-green-100 text-green-700',
  PUT: 'bg-orange-100 text-orange-700', PATCH: 'bg-purple-100 text-purple-700',
  DELETE: 'bg-red-100 text-red-700',
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

  const loadCases = useCallback(async () => {
    try {
      const data: any = await fetchTestCases({ case_type: 'api', page_size: 100 })
      setApiCases(data?.items || [])
    } catch { setApiCases([]) }
  }, [])

  useEffect(() => { loadCases() }, [loadCases])

  const toggleSelect = (id: number) => {
    setSelected(prev => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next })
  }

  const toggleAll = () => {
    if (selected.size === apiCases.length) setSelected(new Set())
    else setSelected(new Set(apiCases.map(c => c.id)))
  }

  const runSingle = async (caseId: number) => {
    setExecutingCase(caseId)
    setResult(null)
    try {
      const res = await executeApiCase(caseId)
      setResult(res as any)
      if (!isBatchResult(res) && res.all_pass) toast.success('全部断言通过')
      else if (!isBatchResult(res)) toast.error(`${res.assertions?.filter((a: ApiAssertionResult) => !a.passed).length || 0} 个断言失败`)
    } catch (e: any) { toast.error(e?.message || '执行失败') }
    finally { setExecutingCase(null) }
  }

  const runBatch = async () => {
    if (!projectId) { toast.error('未选择项目'); return }
    if (selected.size === 0) { toast.error('请至少选择一条用例'); return }
    setLoading(true)
    try {
      const task = await createApiExecutionTask({
        name: `批量执行 ${new Date().toLocaleString('zh-CN')}`,
        case_ids: Array.from(selected),
      })
      toast.success(`批量任务已创建: ${task.task_id}，共 ${task.total} 条用例`)
      // 轮询任务结果
      setTimeout(() => loadCases(), 1000)
    } catch (e: any) { toast.error(e?.message || '创建任务失败') }
    finally { setLoading(false) }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Left: Case list */}
      <div className="lg:col-span-2">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={toggleAll} data-icon="inline-start">
              {selected.size === apiCases.length && apiCases.length > 0 ? <ClipboardCheck className="size-4" /> : <MinusCircle className="size-4" />}
              {selected.size > 0 ? `已选 ${selected.size}` : '全选'}
            </Button>
            <Button size="sm" onClick={runBatch} disabled={loading || selected.size === 0} data-icon="inline-start">
              {loading ? <Loader2 className="animate-spin size-4" /> : <Play className="size-4" />}
              批量执行 ({selected.size})
            </Button>
          </div>
          <span className="text-xs text-muted-foreground">{apiCases.length} 条</span>
        </div>

        <div className="border rounded-lg divide-y max-h-[70vh] overflow-y-auto">
          {apiCases.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <p className="text-sm">暂无 API 用例</p>
              <p className="text-xs mt-1">在「接口资产」中导入接口并生成用例</p>
            </div>
          ) : (
            apiCases.map(c => (
              <div key={c.id} className={`flex items-center gap-3 px-4 py-3 hover:bg-muted/50 cursor-pointer ${selected.has(c.id) ? 'bg-muted/30' : ''}`}>
                <button onClick={() => toggleSelect(c.id)} className="shrink-0">
                  {selected.has(c.id) ? <ClipboardCheck className="size-4 text-primary" /> : <MinusCircle className="size-4 text-muted-foreground" />}
                </button>
                <Badge className={METHOD_COLORS[c.api_method || 'GET'] || ''}>{c.api_method || 'GET'}</Badge>
                <div className="flex-1 min-w-0" onClick={() => runSingle(c.id)}>
                  <p className="text-sm font-medium truncate">{c.title}</p>
                  <p className="text-xs text-muted-foreground truncate">{c.api_endpoint}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Badge variant="outline" className="text-[10px]">{c.priority}</Badge>
                  <Button size="icon-sm" variant="ghost" onClick={() => runSingle(c.id)} disabled={executingCase === c.id}>
                    {executingCase === c.id ? <Loader2 className="animate-spin size-4" /> : <Play className="size-4" />}
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right: Response panel */}
      <div className="lg:col-span-1">
        <ResponsePanel result={result} loading={executingCase !== null} />
      </div>
    </div>
  )
}
