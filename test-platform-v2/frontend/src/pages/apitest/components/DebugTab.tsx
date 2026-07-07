import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Play, Plus, Trash2, Loader2, CheckCircle2, XCircle, Save, FlaskConical } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { quickExecute } from '@/api/apitest'
import { fetchEnvironments } from '@/api/environment'
import { fetchDatasets } from '@/api/dataset'
import type { ApiExecutionResult, ApiAssertionResult, BatchExecutionResult, DatasetListItem, Environment } from '@/types'

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'] as const

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  POST: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  PUT: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  PATCH: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  DELETE: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  HEAD: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  OPTIONS: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
}

function isBatchResult(res: ApiExecutionResult | BatchExecutionResult): res is BatchExecutionResult {
  return 'batch_mode' in res && (res as any).batch_mode
}

export default function DebugTab() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ApiExecutionResult | null>(null)
  const [method, setMethod] = useState<string>('GET')
  const [url, setUrl] = useState('')
  const [headers, setHeaders] = useState('{}')
  const [body, setBody] = useState('')
  const [assertions, setAssertions] = useState('[]')
  const [envId, setEnvId] = useState<number | undefined>()
  const [envs, setEnvs] = useState<Environment[]>([])
  const [datasetId, setDatasetId] = useState<number | undefined>()
  const [datasets, setDatasets] = useState<DatasetListItem[]>([])

  useEffect(() => {
    fetchEnvironments().then(setEnvs).catch(() => {})
    fetchDatasets({ page_size: 100 }).then(d => setDatasets(d.items || [])).catch(() => {})
  }, [])

  const runQuick = async () => {
    if (!url.trim()) { toast.error('请输入 URL'); return }
    setLoading(true)
    setResult(null)
    try {
      const res = await quickExecute({ method, url, headers, body, assertions, environment_id: envId, dataset_id: datasetId })
      setResult(res as any)
      if (isBatchResult(res)) toast.success(`批量执行完成: ${res.passed}/${res.total_rows} 通过`)
      else if (res.all_pass) toast.success('全部断言通过')
      else if (res.assertions?.length) toast.error(`${res.assertions.filter((a: ApiAssertionResult) => !a.passed).length} 个断言失败`)
    } catch (e: any) {
      toast.error(e?.message || '请求失败')
      setResult(e?.response?.data || { status: 'error', status_code: 0, error: e?.message })
    } finally { setLoading(false) }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 space-y-4">
        {/* Env + Dataset selectors */}
        <div className="flex items-center gap-3 flex-wrap">
          {envs.length > 0 && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium whitespace-nowrap">环境:</label>
              <Select value={envId?.toString() || '_none'} onValueChange={(v) => setEnvId(v === '_none' ? undefined : Number(v))}>
                <SelectTrigger className="w-[200px]"><SelectValue placeholder="不使用环境变量" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">不使用环境变量</SelectItem>
                  {envs.map((e) => (
                    <SelectItem key={e.id} value={e.id.toString()}>{e.name} ({e.env_type})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          {datasets.length > 0 && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium whitespace-nowrap">测试数据:</label>
              <Select value={datasetId?.toString() || '_none'} onValueChange={(v) => setDatasetId(v === '_none' ? undefined : Number(v))}>
                <SelectTrigger className="w-[220px]"><SelectValue placeholder="不使用测试数据" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">不使用测试数据</SelectItem>
                  {datasets.map((d) => (
                    <SelectItem key={d.id} value={d.id.toString()}>{d.name} ({d.row_count} 行)</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <Button onClick={runQuick} disabled={loading} data-icon="inline-start" className="ml-auto">
            {loading ? <Loader2 className="animate-spin" /> : <Play />}
            发送
          </Button>
        </div>

        <Card>
          <CardHeader><CardTitle>请求配置</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
              <div className="md:col-span-3">
                <label className="text-sm font-medium mb-1.5 block">方法</label>
                <Select value={method} onValueChange={setMethod}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-9">
                <label className="text-sm font-medium mb-1.5 block">URL <span className="text-destructive">*</span></label>
                <Input placeholder="https://example.com/api/v1/users" value={url} onChange={(e) => setUrl(e.target.value)} />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Headers (JSON)</label>
              <Textarea rows={3} placeholder='{"Content-Type":"application/json"}' value={headers} onChange={(e) => setHeaders(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Body</label>
              <Textarea rows={6} placeholder='{"key":"value"}' value={body} onChange={(e) => setBody(e.target.value)} />
            </div>
          </CardContent>
        </Card>

        <AssertionEditor value={assertions} onChange={setAssertions} />
      </div>

      <div className="lg:col-span-1">
        <ResponsePanel result={result} loading={loading} />
      </div>
    </div>
  )
}

// ── Assertion Editor ──

function AssertionEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [items, setItems] = useState<Array<{ type: string; path: string; expected: string; operator: string; pattern: string; key: string }>>([])
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    try { setItems(JSON.parse(value)) } catch { setItems([]) }
  }, [value])

  const sync = (newItems: typeof items) => {
    setItems(newItems)
    onChange(JSON.stringify(newItems, null, 2))
  }

  const addRule = () => {
    sync([...items, { type: 'status_code', path: '', expected: '200', operator: 'eq', pattern: '', key: '' }])
  }

  const removeRule = (i: number) => sync(items.filter((_, idx) => idx !== i))
  const updateRule = (i: number, field: string, val: string) => {
    const next = [...items]
    ;(next[i] as any)[field] = val
    sync(next)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <CardTitle className="text-sm">断言规则 ({items.length})</CardTitle>
        <Button size="icon-sm" variant="ghost" onClick={(e) => { e.stopPropagation(); addRule() }} title="添加断言"><Plus className="size-4" /></Button>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-3">
          {items.map((rule, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 p-2 border rounded-md">
              <Select value={rule.type} onValueChange={(v) => updateRule(i, 'type', v)}>
                <SelectTrigger className="w-[140px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="status_code">status_code</SelectItem>
                  <SelectItem value="jsonpath">jsonpath</SelectItem>
                  <SelectItem value="regex">regex</SelectItem>
                  <SelectItem value="response_time">response_time</SelectItem>
                  <SelectItem value="header">header</SelectItem>
                  <SelectItem value="type">type</SelectItem>
                  <SelectItem value="array_length">array_length</SelectItem>
                  <SelectItem value="json_schema">json_schema</SelectItem>
                </SelectContent>
              </Select>
              {rule.type === 'header' && (
                <Input className="w-[120px] h-8 text-xs" placeholder="Header名" value={rule.key} onChange={(e) => updateRule(i, 'key', e.target.value)} />
              )}
              {['jsonpath', 'type', 'array_length'].includes(rule.type) && (
                <Input className="w-[140px] h-8 text-xs" placeholder="$.data.code" value={rule.path} onChange={(e) => updateRule(i, 'path', e.target.value)} />
              )}
              {rule.type === 'regex' && (
                <Input className="w-[140px] h-8 text-xs" placeholder="正则表达式" value={rule.pattern} onChange={(e) => updateRule(i, 'pattern', e.target.value)} />
              )}
              <Select value={rule.operator} onValueChange={(v) => updateRule(i, 'operator', v)}>
                <SelectTrigger className="w-[80px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="eq">=</SelectItem>
                  <SelectItem value="neq">≠</SelectItem>
                  <SelectItem value="gt">&gt;</SelectItem>
                  <SelectItem value="lt">&lt;</SelectItem>
                  <SelectItem value="gte">≥</SelectItem>
                  <SelectItem value="lte">≤</SelectItem>
                  <SelectItem value="contains">含</SelectItem>
                  <SelectItem value="exists">存在</SelectItem>
                </SelectContent>
              </Select>
              <Input className="flex-1 min-w-[100px] h-8 text-xs" placeholder="期望值" value={rule.expected} onChange={(e) => updateRule(i, 'expected', e.target.value)} />
              <Button size="icon-sm" variant="ghost" className="text-destructive h-8 w-8" onClick={() => removeRule(i)}>
                <Trash2 className="size-3" />
              </Button>
            </div>
          ))}
          {items.length === 0 && <p className="text-xs text-muted-foreground">暂未配置断言。点击 + 添加。</p>}
        </CardContent>
      )}
    </Card>
  )
}

// ── Response Panel ──

export function ResponsePanel({ result, loading }: { result: any; loading: boolean }) {
  if (result?.batch_mode) {
    const b = result as BatchExecutionResult
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2">批量执行 <Badge className={b.failed === 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>{b.passed}/{b.total_rows}</Badge></CardTitle></CardHeader>
        <CardContent className="space-y-2 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-muted rounded p-2"><div className="text-lg font-bold">{b.total_rows}</div><div className="text-xs text-muted-foreground">总行数</div></div>
            <div className="bg-green-50 dark:bg-green-950/20 rounded p-2"><div className="text-lg font-bold text-green-600">{b.passed}</div><div className="text-xs text-muted-foreground">通过</div></div>
            <div className="bg-red-50 dark:bg-red-950/20 rounded p-2"><div className="text-lg font-bold text-red-600">{b.failed}</div><div className="text-xs text-muted-foreground">失败</div></div>
          </div>
          {b.per_row.map((row) => (
            <div key={row.row_index} className="border rounded p-2 text-xs">
              <span className="font-medium">#{row.row_index + 1}</span>
              <span className="ml-2 text-muted-foreground">{row.result.duration_ms}ms</span>
              {row.result.assertions?.map((a: ApiAssertionResult, i: number) => (
                <div key={i} className={`flex items-center gap-1 mt-1 ${a.passed ? 'text-green-600' : 'text-red-600'}`}>
                  {a.passed ? <CheckCircle2 className="size-3" /> : <XCircle className="size-3" />}
                  <span>{a.message}</span>
                </div>
              ))}
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader><CardTitle>响应结果</CardTitle></CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center"><Loader2 className="animate-spin size-5" /><span>请求中...</span></div>
        ) : result ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className={result.status_code >= 200 && result.status_code < 300 ? 'bg-green-100 text-green-700' : result.status_code > 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}>
                {result.status_code || 'ERR'} {result.status === 'error' ? result.error : ''}
              </Badge>
              <Badge variant="outline">{result.duration_ms || 0} ms</Badge>
              {result.all_pass ? <Badge className="bg-green-100 text-green-700"><CheckCircle2 className="size-3 mr-1" />全部通过</Badge>
                : result.assertions?.length ? <Badge className="bg-red-100 text-red-700"><XCircle className="size-3 mr-1" />断言失败</Badge> : null}
            </div>
            {result.assertions?.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">断言:</p>
                {result.assertions.map((a: ApiAssertionResult, i: number) => (
                  <div key={i} className={`flex items-start gap-1.5 text-xs p-1.5 rounded ${a.passed ? 'bg-green-50 dark:bg-green-950/20' : 'bg-red-50 dark:bg-red-950/20'}`}>
                    {a.passed ? <CheckCircle2 className="size-3 text-green-600 mt-0.5 shrink-0" /> : <XCircle className="size-3 text-red-600 mt-0.5 shrink-0" />}
                    <span>{a.message}</span>
                  </div>
                ))}
              </div>
            )}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">响应体:</p>
              <pre className="text-xs whitespace-pre-wrap break-all bg-muted rounded-lg p-3 max-h-80 overflow-auto">{formatBody(result.response_body)}</pre>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-8 text-center">发送请求后将在这里展示响应。</p>
        )}
      </CardContent>
    </Card>
  )
}

function formatBody(data: any): string {
  if (data === null || data === undefined) return '(空)'
  if (typeof data === 'string') { try { return JSON.stringify(JSON.parse(data), null, 2) } catch { return data } }
  return JSON.stringify(data, null, 2)
}
