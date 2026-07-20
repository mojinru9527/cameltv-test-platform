import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Play, Plus, Trash2, Loader2, CheckCircle2, XCircle } from '@/lib/icons'
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
import AssertionEditor from './AssertionEditor'
import { buildSampleBody, formatBody } from './utils'
import type { ApiEndpoint, ApiExecutionResult, ApiAssertionResult, BatchExecutionResult, DatasetListItem, Environment } from '@/types'

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

const BODY_TYPES = [
  { value: 'json', label: 'JSON' },
  { value: 'form', label: 'form-data' },
  { value: 'x-www-form-urlencoded', label: 'x-www-form-urlencoded' },
  { value: 'raw', label: 'Raw' },
] as const

const TEST_COUNTS = [1, 3, 5] as const

type HeaderRow = { key: string; value: string }
type ParamRow = { key: string; value: string }

function isBatchResult(res: ApiExecutionResult | BatchExecutionResult): res is BatchExecutionResult {
  return 'batch_mode' in res && (res as any).batch_mode
}

/**
 * Compose a full URL from address segments, correctly handling slashes.
 * Example: composeAssetUrl('https://api.example.com', 'api', '/v1/ee/search', '/synonyms/cou')
 *       → 'https://api.example.com/api/v1/ee/search/synonyms/cou'
 */
function composeAssetUrl(baseUrl: string, serviceName: string, modulePath: string, endpointPath: string): string {
  let result = baseUrl.replace(/\/+$/, '')
  if (serviceName) {
    result += '/' + serviceName.replace(/^\/+|\/+$/g, '')
  }
  if (modulePath) {
    const cleaned = modulePath.replace(/\/+$/g, '')
    result += cleaned.startsWith('/') ? cleaned : '/' + cleaned
  }
  if (endpointPath) {
    const cleaned = endpointPath.replace(/\/+$/g, '')
    result += cleaned.startsWith('/') ? cleaned : '/' + cleaned
  }
  return result
}

interface Props {
  endpoint?: ApiEndpoint | null
}

export default function DebugTab({ endpoint }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ApiExecutionResult | null>(null)
  const [method, setMethod] = useState<string>('GET')
  const [baseUrl, setBaseUrl] = useState('')
  const [serviceName, setServiceName] = useState('')
  const [modulePath, setModulePath] = useState('')
  const [endpointPath, setEndpointPath] = useState('')
  const [testCount, setTestCount] = useState(5)
  const [bodyType, setBodyType] = useState<string>('json')
  const [body, setBody] = useState('')
  const [headersJson, setHeadersJson] = useState('{}')
  const [assertions, setAssertions] = useState('[]')
  const [envId, setEnvId] = useState<number | undefined>()
  const [envs, setEnvs] = useState<Environment[]>([])
  const [datasetId, setDatasetId] = useState<number | undefined>()
  const [datasets, setDatasets] = useState<DatasetListItem[]>([])

  // P2: Multi-format — header table + params table
  const [headerRows, setHeaderRows] = useState<HeaderRow[]>([{ key: 'Content-Type', value: 'application/json' }])
  const [paramRows, setParamRows] = useState<ParamRow[]>([])
  const [headerMode, setHeaderMode] = useState<'table' | 'json'>('table')

  useEffect(() => {
    let cancelled = false
    fetchEnvironments().then((data) => {
      if (cancelled) return
      setEnvs(data)
      // 默认选中「测试5」环境
      if (envId === undefined) {
        const defaultEnv = data.find((e: Environment) => e.name === '测试5')
        if (defaultEnv) {
          setEnvId(defaultEnv.id)
          setBaseUrl(defaultEnv.base_url)
        }
      }
    }).catch(() => {})
    fetchDatasets({ page_size: 100 }).then(d => { if (!cancelled) setDatasets(d.items || []) }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  // Pre-fill from endpoint asset
  useEffect(() => {
    if (!endpoint) return
    setMethod(endpoint.method || 'GET')

    // Parse path to pre-fill address fields:
    // first segment → serviceName, last segment → endpointPath, middle → modulePath
    const path = endpoint.path || ''
    const segments = path.split('/').filter(Boolean)
    if (segments.length > 0) {
      setServiceName(segments[0])
      if (segments.length > 1) {
        const last = segments[segments.length - 1]
        const middle = segments.slice(1, -1)
        setModulePath(middle.length > 0 ? '/' + middle.join('/') : '')
        setEndpointPath('/' + last)
      } else {
        setModulePath('')
        setEndpointPath('')
      }
    }

    // Parse request_schema to pre-fill headers/body/params
    try {
      const schema = typeof endpoint.request_schema === 'string'
        ? JSON.parse(endpoint.request_schema)
        : endpoint.request_schema || {}

      // Pre-fill query params
      if (schema.query && Array.isArray(schema.query)) {
        const qp: ParamRow[] = schema.query
          .filter((p: any) => p.required)
          .map((p: any) => ({ key: p.name, value: '' }))
        if (qp.length > 0) setParamRows(qp)
      }

      // Pre-fill body from schema (shared util returns JSON string)
      if (schema.body?.properties) {
        setBody(buildSampleBody(schema.body.properties))
        setBodyType('json')
        setHeaderRows([{ key: 'Content-Type', value: 'application/json' }])
      }
    } catch {
      // ignore parse errors
    }
  }, [endpoint])

  const buildHeaders = (): string => {
    if (headerMode === 'json') return headersJson
    const h: Record<string, string> = {}
    headerRows.filter(r => r.key.trim()).forEach(r => { h[r.key.trim()] = r.value })
    return JSON.stringify(h)
  }

  const buildUrl = (): string => {
    const base = composeAssetUrl(baseUrl, serviceName, modulePath, endpointPath)
    if (paramRows.length === 0) return base
    const qs = paramRows
      .filter(r => r.key.trim())
      .map(r => `${encodeURIComponent(r.key.trim())}=${encodeURIComponent(r.value)}`)
      .join('&')
    if (!qs) return base
    return base.includes('?') ? `${base}&${qs}` : `${base}?${qs}`
  }

  // Auto-scroll to response when result changes
  useEffect(() => {
    if (result) {
      setTimeout(() => {
        document.getElementById('response-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    }
  }, [result])

  const runQuick = async () => {
    const composed = composeAssetUrl(baseUrl, serviceName, modulePath, endpointPath)
    if (!composed) { toast.error('请填写接口地址'); return }
    setLoading(true)
    setResult(null)
    try {
      // When a dataset is selected, backend handles batch per-row;
      // otherwise repeat the same request sequentially testCount times.
      const times = datasetId ? 1 : testCount
      let lastResult: any = null
      for (let i = 0; i < times; i++) {
        const res = await quickExecute({
          method,
          url: buildUrl(),
          headers: buildHeaders(),
          body: bodyType === 'json' ? body : body,
          assertions,
          environment_id: envId,
          dataset_id: datasetId,
        })
        lastResult = res
      }
      setResult(lastResult as any)
      if (isBatchResult(lastResult)) toast.success(`批量执行完成: ${lastResult.passed}/${lastResult.total_rows} 通过`)
      else if (lastResult.all_pass) toast.success('全部断言通过')
      else if (lastResult.assertions?.length) toast.error(`${lastResult.assertions.filter((a: ApiAssertionResult) => !a.passed).length} 个断言失败`)
    } catch (e: any) {
      toast.error(e?.message || '请求失败')
      setResult(e?.response?.data || { status: 'error', status_code: 0, error: e?.message })
    } finally { setLoading(false) }
  }

  // ── Header table helpers ──
  const addHeaderRow = () => setHeaderRows([...headerRows, { key: '', value: '' }])
  const removeHeaderRow = (i: number) => setHeaderRows(headerRows.filter((_, idx) => idx !== i))
  const updateHeaderRow = (i: number, field: 'key' | 'value', val: string) => {
    const next = [...headerRows]
    next[i][field] = val
    setHeaderRows(next)
    // Auto-update Content-Type when body type changes
    if (field === 'key' && val.toLowerCase() === 'content-type') {
      if (bodyType === 'json') next[i].value = 'application/json'
      else if (bodyType === 'form') next[i].value = 'multipart/form-data'
      else if (bodyType === 'x-www-form-urlencoded') next[i].value = 'application/x-www-form-urlencoded'
    }
  }

  // ── Param table helpers ──
  const addParamRow = () => setParamRows([...paramRows, { key: '', value: '' }])
  const removeParamRow = (i: number) => setParamRows(paramRows.filter((_, idx) => idx !== i))
  const updateParamRow = (i: number, field: 'key' | 'value', val: string) => {
    const next = [...paramRows]
    next[i][field] = val
    setParamRows(next)
  }

  const urlPreview = composeAssetUrl(baseUrl, serviceName, modulePath, endpointPath)

  return (
    <div className="space-y-4">
      {/* Top bar: Env + Dataset + TestCount selectors + Send button */}
      <div className="flex items-center gap-3 flex-wrap">
        {envs.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium whitespace-nowrap">环境:</label>
            <Select value={envId?.toString() || '_none'} onValueChange={(v) => {
              if (v === '_none') { setEnvId(undefined); return }
              const id = Number(v)
              setEnvId(id)
              const env = envs.find(e => e.id === id)
              if (env) setBaseUrl(env.base_url)
            }}>
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
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium whitespace-nowrap">次数:</label>
          <Select value={testCount.toString()} onValueChange={(v) => setTestCount(Number(v))}>
            <SelectTrigger className="w-[80px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {TEST_COUNTS.map((n) => <SelectItem key={n} value={n.toString()}>{n}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={runQuick} disabled={loading} data-icon="inline-start" className="ml-auto">
          {loading ? <Loader2 className="animate-spin" /> : <Play />}
          发送
        </Button>
      </div>

      {/* Request Config Card */}
      <Card>
        <CardHeader><CardTitle>请求配置</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {/* Method */}
          <div>
            <label className="text-sm font-medium mb-1.5 block">方法</label>
            <Select value={method} onValueChange={setMethod}>
              <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Split address fields — 2x2 grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1.5 block">服务器地址</label>
              <Input
                placeholder="https://api.example.com"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                aria-label="服务器地址"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">服务名</label>
              <Input
                placeholder="api"
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                aria-label="服务名"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">模块路径</label>
              <Input
                placeholder="/ee/search"
                value={modulePath}
                onChange={(e) => setModulePath(e.target.value)}
                aria-label="模块路径"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">接口路径</label>
              <Input
                placeholder="/synonyms/cou"
                value={endpointPath}
                onChange={(e) => setEndpointPath(e.target.value)}
                aria-label="接口路径"
              />
            </div>
          </div>

          {/* URL preview */}
          <div className="bg-muted/50 rounded-md px-3 py-2">
            <span className="text-xs text-muted-foreground font-mono break-all">
              {urlPreview || '(未设置)'}
            </span>
          </div>

          {/* P2: Params table */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium">Params (Query)</label>
              <Button size="icon-sm" variant="ghost" onClick={addParamRow} title="添加参数"><Plus className="size-3" /></Button>
            </div>
            {paramRows.length > 0 && (
              <div className="border rounded-md divide-y">
                {paramRows.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 px-2 py-1.5">
                    <Input className="flex-1 h-7 text-xs" placeholder="参数名" value={r.key} onChange={(e) => updateParamRow(i, 'key', e.target.value)} aria-label={`参数 ${i + 1} 名称`} />
                    <Input className="flex-1 h-7 text-xs" placeholder="参数值" value={r.value} onChange={(e) => updateParamRow(i, 'value', e.target.value)} aria-label={`参数 ${i + 1} 值`} />
                    <Button size="icon-sm" variant="ghost" className="text-destructive h-7 w-7 shrink-0" onClick={() => removeParamRow(i)}><Trash2 className="size-3" /></Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* P2: Headers — table or JSON mode */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium">Headers</label>
              <div className="flex items-center gap-1">
                <Button size="sm" variant={headerMode === 'table' ? 'default' : 'outline'} className="h-7 text-xs px-2" onClick={() => setHeaderMode('table')}>表格</Button>
                <Button size="sm" variant={headerMode === 'json' ? 'default' : 'outline'} className="h-7 text-xs px-2" onClick={() => setHeaderMode('json')}>JSON</Button>
                {headerMode === 'table' && <Button size="icon-sm" variant="ghost" onClick={addHeaderRow} title="添加 Header"><Plus className="size-3" /></Button>}
              </div>
            </div>
            {headerMode === 'table' ? (
              <div className="border rounded-md divide-y">
                {headerRows.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 px-2 py-1.5">
                    <Input className="flex-1 h-7 text-xs" placeholder="Header 名" value={r.key} onChange={(e) => updateHeaderRow(i, 'key', e.target.value)} aria-label={`Header ${i + 1} 名称`} />
                    <Input className="flex-1 h-7 text-xs" placeholder="Header 值" value={r.value} onChange={(e) => updateHeaderRow(i, 'value', e.target.value)} aria-label={`Header ${i + 1} 值`} />
                    <Button size="icon-sm" variant="ghost" className="text-destructive h-7 w-7 shrink-0" onClick={() => removeHeaderRow(i)}><Trash2 className="size-3" /></Button>
                  </div>
                ))}
              </div>
            ) : (
              <Textarea rows={3} placeholder='{"Content-Type":"application/json"}' value={headersJson} onChange={(e) => setHeadersJson(e.target.value)} aria-label="Headers JSON" />
            )}
          </div>

          {/* P2: Body type selector + Body editor */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium">Body</label>
              <Select value={bodyType} onValueChange={setBodyType}>
                <SelectTrigger className="w-[180px] h-7 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {BODY_TYPES.map(bt => <SelectItem key={bt.value} value={bt.value}>{bt.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Textarea
              rows={bodyType === 'form' ? 4 : 6}
              placeholder={
                bodyType === 'json' ? '{"key":"value"}'
                  : bodyType === 'form' ? 'key1=value1\nkey2=value2'
                  : bodyType === 'x-www-form-urlencoded' ? 'key1=value1&key2=value2'
                  : 'Raw body content...'
              }
              value={body}
              onChange={(e) => setBody(e.target.value)}
              aria-label="请求 Body"
            />
          </div>
        </CardContent>
      </Card>

      <AssertionEditor value={assertions} onChange={setAssertions} />

      {/* Response panel — full width below config */}
      <ResponsePanel result={result} loading={loading} />
    </div>
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
    <Card id="response-panel">
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
