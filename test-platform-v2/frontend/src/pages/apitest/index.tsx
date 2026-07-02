import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Play, Save, Plus, Trash2, Code2, Loader2, CheckCircle2, XCircle, FlaskConical, FileText } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import PageHeader from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import { executeApiCase, quickExecute } from '@/api/apitest'
import { fetchEnvironments } from '@/api/environment'
import { fetchTestCases } from '@/api/testcase'
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

export default function ApiTestPage() {
  const currentProjectId = useAuthStore((state) => state.currentProjectId)
  const [activeTab, setActiveTab] = useState('quick')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ApiExecutionResult | null>(null)

  // ── Quick debug state ──
  const [method, setMethod] = useState<string>('GET')
  const [url, setUrl] = useState('')
  const [headers, setHeaders] = useState('{}')
  const [body, setBody] = useState('')
  const [assertions, setAssertions] = useState('[]')
  const [envId, setEnvId] = useState<number | undefined>()
  const [envs, setEnvs] = useState<Environment[]>([])
  const [datasetId, setDatasetId] = useState<number | undefined>()
  const [datasets, setDatasets] = useState<DatasetListItem[]>([])

  // ── Saved cases state ──
  const [apiCases, setApiCases] = useState<any[]>([])
  const [selectedCase, setSelectedCase] = useState<any>(null)

  useEffect(() => {
    fetchEnvironments().then(setEnvs).catch(() => {})
    fetchDatasets({ page_size: 100 }).then(d => setDatasets(d.items || [])).catch(() => {})
  }, [])

  // Load api-type cases
  const loadApiCases = useCallback(async () => {
    try {
      const data: any = await fetchTestCases({ case_type: 'api', page_size: 100 })
      setApiCases(data?.items || [])
    } catch { setApiCases([]) }
  }, [])

  useEffect(() => {
    if (activeTab === 'cases') loadApiCases()
  }, [activeTab, loadApiCases])

  // ── Execute ──
  const runQuick = async () => {
    if (!url.trim()) { toast.error('请输入 URL'); return }
    setLoading(true)
    setResult(null)
    try {
      const res = await quickExecute({ method, url, headers, body, assertions, environment_id: envId, dataset_id: datasetId })
      setResult(res as any)
      if ((res as any).batch_mode) {
        const b = res as any as BatchExecutionResult
        toast.success(`批量执行完成: ${b.passed}/${b.total_rows} 通过`)
      } else if (res.all_pass) toast.success('全部断言通过')
      else if (res.assertions?.length) toast.error(`${res.assertions.filter((a: ApiAssertionResult) => !a.passed).length} 个断言失败`)
    } catch (e: any) {
      toast.error(e?.message || '请求失败')
      setResult(e?.response?.data || { status: 'error', status_code: 0, error: e?.message })
    } finally { setLoading(false) }
  }

  const runSaved = async () => {
    if (!selectedCase) return
    setLoading(true)
    setResult(null)
    try {
      const res = await executeApiCase(selectedCase.id, envId, datasetId)
      setResult(res as any)
      if ((res as any).batch_mode) {
        const b = res as any as BatchExecutionResult
        toast.success(`批量执行完成: ${b.passed}/${b.total_rows} 通过`)
      } else if (res.all_pass) toast.success('全部断言通过')
      else if (res.assertions?.length) toast.error(`${res.assertions.filter((a: ApiAssertionResult) => !a.passed).length} 个断言失败`)
    } catch (e: any) {
      toast.error(e?.message || '执行失败')
      setResult(e?.response?.data || { status: 'error', status_code: 0, error: e?.message })
    } finally { setLoading(false) }
  }

  const selectCase = (c: any) => {
    setSelectedCase(c)
    // Pre-fill form fields if needed
  }

  return (
    <div className="space-y-4">
      <PageHeader title="接口测试" description="服务端执行 HTTP 请求，支持变量替换和断言验证。">
        <Button variant="outline" onClick={() => { setResult(null); loadApiCases() }}>
          清空结果
        </Button>
        {activeTab === 'quick' && (
          <Button onClick={runQuick} disabled={loading} data-icon="inline-start">
            {loading ? <Loader2 className="animate-spin" /> : <Play />}
            发送
          </Button>
        )}
        {activeTab === 'cases' && selectedCase && (
          <Button onClick={runSaved} disabled={loading} data-icon="inline-start">
            {loading ? <Loader2 className="animate-spin" /> : <Play />}
            执行
          </Button>
        )}
      </PageHeader>

      {/* Environment + Dataset selectors - shared */}
      <div className="flex items-center gap-3 flex-wrap">
        {envs.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium whitespace-nowrap">环境:</label>
            <Select value={envId?.toString() || '_none'} onValueChange={(v) => setEnvId(v === '_none' ? undefined : Number(v))}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="不使用环境变量" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">不使用环境变量</SelectItem>
                {envs.map((e) => (
                  <SelectItem key={e.id} value={e.id.toString()}>
                    {e.name} ({e.env_type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {envId && (
              <p className="text-xs text-muted-foreground">$&#123;VAR&#125; 自动替换</p>
            )}
          </div>
        )}

        {datasets.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium whitespace-nowrap">测试数据:</label>
            <Select value={datasetId?.toString() || '_none'} onValueChange={(v) => setDatasetId(v === '_none' ? undefined : Number(v))}>
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="不使用测试数据" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">不使用测试数据</SelectItem>
                {datasets.map((d) => (
                  <SelectItem key={d.id} value={d.id.toString()}>
                    {d.name} ({d.row_count} 行)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {datasetId && (
              <p className="text-xs text-muted-foreground">$&#123;列名&#125; 按行替换</p>
            )}
          </div>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="quick">
            <FlaskConical className="size-4 mr-1" />
            快速调试
          </TabsTrigger>
          <TabsTrigger value="cases">
            <FileText className="size-4 mr-1" />
            API 用例
          </TabsTrigger>
        </TabsList>

        {/* ── Quick Debug Tab ── */}
        <TabsContent value="quick" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
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
                    <label className="text-sm font-medium mb-1.5 block">Body (JSON)</label>
                    <Textarea rows={6} placeholder='{"key":"value"}' value={body} onChange={(e) => setBody(e.target.value)} />
                  </div>
                </CardContent>
              </Card>

              {/* Assertions editor */}
              <AssertionEditor value={assertions} onChange={setAssertions} />
            </div>

            {/* Response panel */}
            <div className="lg:col-span-1">
              <ResponsePanel result={result} loading={loading} />
            </div>
          </div>
        </TabsContent>

        {/* ── Saved Cases Tab ── */}
        <TabsContent value="cases" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-1">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>API 用例</CardTitle>
                  <span className="text-xs text-muted-foreground">{apiCases.length} 条</span>
                </CardHeader>
                <CardContent className="p-0 max-h-[60vh] overflow-y-auto">
                  {apiCases.length === 0 ? (
                    <p className="text-sm text-muted-foreground p-4">暂无 API 类型用例。去「用例服务」创建 case_type=api 的用例。</p>
                  ) : (
                    <ul className="divide-y">
                      {apiCases.map((c) => (
                        <li
                          key={c.id}
                          className={`flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-muted transition-colors ${selectedCase?.id === c.id ? 'bg-muted' : ''}`}
                          onClick={() => selectCase(c)}
                        >
                          <Badge className={METHOD_COLORS[c.api_method || 'GET'] || ''}>{c.api_method || 'GET'}</Badge>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{c.title}</p>
                            <p className="text-xs text-muted-foreground truncate">{c.api_endpoint}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-2 space-y-4">
              {selectedCase ? (
                <>
                  <Card>
                    <CardHeader><CardTitle>{selectedCase.title}</CardTitle></CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div className="flex gap-2">
                        <Badge className={METHOD_COLORS[selectedCase.api_method || 'GET'] || ''}>{selectedCase.api_method || 'GET'}</Badge>
                        <code className="text-xs bg-muted px-2 py-0.5 rounded">{selectedCase.api_endpoint}</code>
                        <Badge variant="outline">{selectedCase.priority}</Badge>
                      </div>
                      {selectedCase.api_headers && selectedCase.api_headers !== '{}' && (
                        <div>
                          <span className="font-medium">Headers:</span>
                          <pre className="text-xs mt-0.5 bg-muted p-2 rounded max-h-24 overflow-auto">{safeFormatJson(selectedCase.api_headers)}</pre>
                        </div>
                      )}
                      {selectedCase.api_body && (
                        <div>
                          <span className="font-medium">Body:</span>
                          <pre className="text-xs mt-0.5 bg-muted p-2 rounded max-h-24 overflow-auto">{safeFormatJson(selectedCase.api_body)}</pre>
                        </div>
                      )}
                      {selectedCase.api_assertions && selectedCase.api_assertions !== '[]' && (
                        <div>
                          <span className="font-medium">断言:</span>
                          <pre className="text-xs mt-0.5 bg-muted p-2 rounded max-h-24 overflow-auto">{safeFormatJson(selectedCase.api_assertions)}</pre>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                  <ResponsePanel result={result} loading={loading} />
                </>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground">
                    <Code2 className="size-8 mx-auto mb-2 opacity-50" />
                    <p>选择左侧 API 用例后点击「执行」</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ── Assertion Editor ──

function AssertionEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [items, setItems] = useState<Array<{ type: string; path: string; expected: string; operator: string; pattern: string }>>([])
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    try { setItems(JSON.parse(value)) } catch { setItems([]) }
  }, [value])

  const sync = (newItems: typeof items) => {
    setItems(newItems)
    onChange(JSON.stringify(newItems, null, 2))
  }

  const addRule = () => {
    sync([...items, { type: 'status_code', path: '', expected: '200', operator: 'eq', pattern: '' }])
    setExpanded(true)
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
        <Button size="icon-sm" variant="ghost" onClick={(e) => { e.stopPropagation(); addRule() }} title="添加断言">
          <Plus className="size-4" />
        </Button>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-3">
          {items.map((rule, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 p-2 border rounded-md">
              <Select value={rule.type} onValueChange={(v) => updateRule(i, 'type', v)}>
                <SelectTrigger className="w-[130px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="status_code">status_code</SelectItem>
                  <SelectItem value="jsonpath">jsonpath</SelectItem>
                  <SelectItem value="regex">regex</SelectItem>
                  <SelectItem value="response_time">response_time</SelectItem>
                </SelectContent>
              </Select>
              {rule.type === 'jsonpath' && (
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

function ResponsePanel({ result, loading }: { result: any; loading: boolean }) {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  const toggleRow = (idx: number) => {
    setExpandedRows(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx) else next.add(idx)
      return next
    })
  }

  // Batch mode result
  if (result?.batch_mode) {
    const b = result as BatchExecutionResult
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            批量执行结果
            <Badge className={b.failed === 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
              {b.passed}/{b.total_rows} 通过
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-muted rounded p-2">
              <div className="text-lg font-bold">{b.total_rows}</div>
              <div className="text-xs text-muted-foreground">总行数</div>
            </div>
            <div className="bg-green-50 dark:bg-green-950/20 rounded p-2">
              <div className="text-lg font-bold text-green-600">{b.passed}</div>
              <div className="text-xs text-muted-foreground">通过</div>
            </div>
            <div className="bg-red-50 dark:bg-red-950/20 rounded p-2">
              <div className="text-lg font-bold text-red-600">{b.failed}</div>
              <div className="text-xs text-muted-foreground">失败</div>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">每行详情:</p>
            {b.per_row.map((row) => (
              <div key={row.row_index} className="border rounded-md">
                <div
                  className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-muted text-xs ${row.result.all_pass ? '' : 'bg-red-50 dark:bg-red-950/10'}`}
                  onClick={() => toggleRow(row.row_index)}
                >
                  {row.result.all_pass
                    ? <CheckCircle2 className="size-3 text-green-600 shrink-0" />
                    : <XCircle className="size-3 text-red-600 shrink-0" />}
                  <span className="font-medium">#{row.row_index + 1}</span>
                  <span className="text-muted-foreground truncate flex-1">
                    {b.columns.slice(0, 3).map(c => `${c}=${row.row_data[c] ?? '-'}`).join(', ')}
                  </span>
                  <span className="text-muted-foreground">{row.result.duration_ms}ms</span>
                  <span className="text-xs">{expandedRows.has(row.row_index) ? '▲' : '▼'}</span>
                </div>
                {expandedRows.has(row.row_index) && (
                  <div className="px-3 pb-3 space-y-2 border-t pt-2">
                    {/* Row data */}
                    <div className="text-xs">
                      <span className="text-muted-foreground">数据: </span>
                      {Object.entries(row.row_data).map(([k, v]) => (
                        <span key={k} className="inline-block mr-2"><code>{k}</code>={v}</span>
                      ))}
                    </div>
                    {/* Assertions */}
                    {row.result.assertions?.length > 0 && (
                      <div className="space-y-0.5">
                        {row.result.assertions.map((a: ApiAssertionResult, i: number) => (
                          <div key={i} className={`flex items-start gap-1 text-xs p-1 rounded ${a.passed ? 'bg-green-50' : 'bg-red-50'}`}>
                            {a.passed ? <CheckCircle2 className="size-3 text-green-600 mt-0.5 shrink-0" /> : <XCircle className="size-3 text-red-600 mt-0.5 shrink-0" />}
                            <span>{a.message}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {/* Response */}
                    <div>
                      <p className="text-xs text-muted-foreground">响应:</p>
                      <pre className="text-xs bg-muted p-2 rounded max-h-32 overflow-auto">{formatBody(row.result.response_body)}</pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  // Regular result
  return (
    <Card>
      <CardHeader><CardTitle>响应结果</CardTitle></CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center">
            <Loader2 className="animate-spin size-5" />
            <span>请求中...</span>
          </div>
        ) : result ? (
          <div className="space-y-3">
            {/* Status */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className={result.status_code >= 200 && result.status_code < 300
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : result.status_code > 0
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  : 'bg-gray-100 text-gray-700'
              }>
                {result.status_code || 'ERR'} {result.status === 'error' ? result.error : ''}
              </Badge>
              <Badge variant="outline">{result.duration_ms || 0} ms</Badge>
              {result.all_pass ? (
                <Badge className="bg-green-100 text-green-700"><CheckCircle2 className="size-3 mr-1" />全部通过</Badge>
              ) : result.assertions?.length ? (
                <Badge className="bg-red-100 text-red-700"><XCircle className="size-3 mr-1" />断言失败</Badge>
              ) : null}
            </div>

            {/* Assertions */}
            {result.assertions && result.assertions.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">断言详情:</p>
                {result.assertions.map((a: ApiAssertionResult, i: number) => (
                  <div key={i} className={`flex items-start gap-1.5 text-xs p-1.5 rounded ${a.passed ? 'bg-green-50 dark:bg-green-950/20' : 'bg-red-50 dark:bg-red-950/20'}`}>
                    {a.passed ? <CheckCircle2 className="size-3 text-green-600 mt-0.5 shrink-0" /> : <XCircle className="size-3 text-red-600 mt-0.5 shrink-0" />}
                    <span>{a.message}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Response body */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">响应体:</p>
              <pre className="text-xs whitespace-pre-wrap break-all bg-muted rounded-lg p-3 max-h-80 overflow-auto">
                {formatBody(result.response_body)}
              </pre>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-8 text-center">发送请求后将在这里展示响应。</p>
        )}
      </CardContent>
    </Card>
  )
}

// ── Helpers ──

function safeFormatJson(raw: string | undefined): string {
  if (!raw) return ''
  try { return JSON.stringify(JSON.parse(raw), null, 2) } catch { return raw }
}

function formatBody(data: any): string {
  if (data === null || data === undefined) return '(空)'
  if (typeof data === 'string') {
    try { return JSON.stringify(JSON.parse(data), null, 2) } catch { return data }
  }
  return JSON.stringify(data, null, 2)
}
