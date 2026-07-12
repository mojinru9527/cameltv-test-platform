import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { FlaskConical, Plus, Trash2 } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { fetchEnvironments, updateEnvironment } from '@/api/environment'
import { quickExecute } from '@/api/apitest'
import { ResponsePanel } from './DebugTab'
import EnvironmentBar from './EnvironmentBar'
import { normalizeJson, defaultAssertions, buildSampleBody } from './utils'
import type { ApiEndpoint, ApiExecutionResult, Environment } from '@/types'

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-blue-100 text-blue-700',
  POST: 'bg-green-100 text-green-700',
  PUT: 'bg-orange-100 text-orange-700',
  PATCH: 'bg-purple-100 text-purple-700',
  DELETE: 'bg-red-100 text-red-700',
}

type QueryRow = { key: string; value: string; enabled: boolean; required: boolean; desc: string }
type PathRow = { key: string; value: string; desc: string }
type HeaderRow = { key: string; value: string; enabled: boolean }

interface DebugSource {
  id: number | string
  method: string
  path: string
  title?: string
  module?: string
  requestSchema?: any
  headers?: any
  body?: string
  assertions?: any
}

interface Props {
  endpoint?: ApiEndpoint | null
  caseItem?: any | null
  serviceName?: string
  emptyTitle?: string
  emptyDescription?: string
}

export default function ApiDebugPanel({
  endpoint,
  caseItem,
  serviceName = '',
  emptyTitle = '选择接口开始调试',
  emptyDescription = '点击左侧接口查看参数并发送请求',
}: Props) {
  const source = useMemo<DebugSource | null>(() => {
    if (endpoint) {
      return {
        id: `endpoint-${endpoint.id}`,
        method: endpoint.method || 'GET',
        path: endpoint.path || '',
        title: endpoint.summary || endpoint.path,
        module: endpoint.module,
        requestSchema: endpoint.request_schema,
      }
    }
    if (caseItem) {
      return {
        id: `case-${caseItem.id}`,
        method: caseItem.api_method || 'GET',
        path: caseItem.api_endpoint || '',
        title: caseItem.title,
        module: caseItem.module,
        headers: caseItem.api_headers,
        body: caseItem.api_body || '',
        assertions: caseItem.api_assertions,
      }
    }
    return null
  }, [caseItem, endpoint])
  const effectiveServiceName = serviceName || extractServiceName(caseItem)

  const [envs, setEnvs] = useState<Environment[]>([])
  const [envId, setEnvId] = useState<number | undefined>()
  const [envBaseUrl, setEnvBaseUrl] = useState('')
  const [queryRows, setQueryRows] = useState<QueryRow[]>([])
  const [pathRows, setPathRows] = useState<PathRow[]>([])
  const [headerRows, setHeaderRows] = useState<HeaderRow[]>([])
  const [body, setBody] = useState('')
  const [bodyType, setBodyType] = useState<'json' | 'raw' | 'none'>('none')
  const [assertions, setAssertions] = useState('[]')
  const [result, setResult] = useState<ApiExecutionResult | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchEnvironments().then((rows) => {
      if (cancelled) return
      setEnvs(rows)
      const testEnv = rows.find(e => e.env_type === 'test') || rows[0]
      if (testEnv) setEnvId(testEnv.id)
    }).catch(() => { if (!cancelled) setEnvs([]) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!envId) { setEnvBaseUrl(''); return }
    setEnvBaseUrl(envs.find(e => e.id === envId)?.base_url || '')
  }, [envId, envs])

  useEffect(() => {
    setResult(null)
    setLoading(false)

    if (!source) {
      setQueryRows([])
      setPathRows([])
      setHeaderRows([])
      setBody('')
      setBodyType('none')
      setAssertions('[]')
      return
    }

    if (endpoint) {
      const schema = normalizeJson(source.requestSchema, {})
      setQueryRows((schema.query || []).map((q: any) => ({
        key: q.name || '',
        value: '',
        enabled: !!q.required,
        required: !!q.required,
        desc: q.description || '',
      })))
      setPathRows((schema.path || []).map((p: any) => ({
        key: p.name || '',
        value: '',
        desc: p.description || '',
      })))

      const headers = (schema.header || []).map((h: any) => ({
        key: h.name || '',
        value: '',
        enabled: !!h.required,
      }))
      setHeaderRows(headers.length ? headers : [{ key: 'Content-Type', value: 'application/json', enabled: true }])

      const bodySchema = schema.body || {}
      if (bodySchema.properties && Object.keys(bodySchema.properties).length > 0) {
        setBody(buildSampleBody(bodySchema.properties))
        setBodyType('json')
      } else {
        setBody('{}')
        setBodyType('json')
      }

      setAssertions(defaultAssertions())
      return
    }

    const parsedHeaders = normalizeJson(source.headers, {})
    setHeaderRows(Object.keys(parsedHeaders).length
      ? Object.entries(parsedHeaders).map(([key, value]) => ({ key, value: String(value ?? ''), enabled: true }))
      : [{ key: 'Content-Type', value: 'application/json', enabled: true }])
    setQueryRows([])
    setPathRows([])
    setBody(source.body || '{}')
    setBodyType('json')
    setAssertions(source.assertions
      ? JSON.stringify(normalizeJson(source.assertions, []), null, 2)
      : '[]')
  }, [endpoint, source])

  const addHeader = () => setHeaderRows(prev => [...prev, { key: '', value: '', enabled: true }])
  const removeHeader = (index: number) => setHeaderRows(prev => prev.filter((_, i) => i !== index))

  const handleSend = async () => {
    if (!source) return
    if (!envId) { toast.error('请先选择环境'); return }

    setLoading(true)
    setResult(null)
    try {
      const enabledQueries: Record<string, string> = {}
      queryRows.filter(r => r.enabled && r.key.trim()).forEach(r => { enabledQueries[r.key.trim()] = r.value })

      const enabledHeaders: Record<string, string> = {}
      headerRows.filter(r => r.enabled && r.key.trim()).forEach(r => { enabledHeaders[r.key.trim()] = r.value })

      let finalPath = source.path
      pathRows.forEach(r => {
        if (r.key && r.value) finalPath = finalPath.replace(`{${r.key}}`, r.value)
      })

      const res = await quickExecute({
        method: source.method,
        url: finalPath,
        headers: JSON.stringify(enabledHeaders),
        body: bodyType === 'none' ? '' : body,
        assertions,
        environment_id: envId,
        service_name: effectiveServiceName,
        query_params: JSON.stringify(enabledQueries),
      })
      setResult(res as ApiExecutionResult)
    } catch (e: any) {
      setResult({
        status: 'error',
        status_code: 0,
        response_headers: {},
        response_body: null,
        duration_ms: 0,
        assertions: [],
        all_pass: false,
        error: e?.message || '请求失败',
      } as any)
    } finally {
      setLoading(false)
    }
  }

  if (!source) {
    return (
      <div className="h-full min-h-[360px] flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <FlaskConical className="size-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">{emptyTitle}</p>
          <p className="text-xs mt-1">{emptyDescription}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full min-h-[520px]">
      <div className="px-3 py-2 border-b bg-muted/20 shrink-0">
        <div className="flex items-center gap-2">
          <Badge className={`text-[10px] ${METHOD_COLORS[source.method] || ''}`}>{source.method}</Badge>
          <code className="text-xs font-medium truncate flex-1">{source.path}</code>
        </div>
        {source.title && <p className="text-[11px] text-muted-foreground mt-0.5 truncate">{source.title}</p>}
      </div>

      <div className="overflow-y-auto flex-1">
        <div className="p-3 space-y-3">
          <EnvironmentBar
            envs={envs}
            envId={envId}
            envBaseUrl={envBaseUrl}
            onEnvChange={(id) => setEnvId(id)}
            onBaseUrlChange={(url) => setEnvBaseUrl(url)}
            onBaseUrlBlur={() => {
              if (envId && envBaseUrl) updateEnvironment(envId, { base_url: envBaseUrl }).catch(() => {})
            }}
          />

          {pathRows.length > 0 && (
            <div>
              <Label className="text-[11px] text-muted-foreground">Path 参数</Label>
              <div className="space-y-1 mt-1">
                {pathRows.map((r, i) => (
                  <Input key={`${r.key}-${i}`} className="h-8 text-xs" placeholder={r.key}
                    value={r.value} aria-label={`Path 参数 ${r.key}`}
                    onChange={e => setPathRows(prev => prev.map((row, idx) => idx === i ? { ...row, value: e.target.value } : row))}
                  />
                ))}
              </div>
            </div>
          )}

          {queryRows.length > 0 && (
            <div>
              <Label className="text-[11px] text-muted-foreground">Query 参数</Label>
              <div className="space-y-1 mt-1">
                {queryRows.map((r, i) => (
                  <div key={`${r.key}-${i}`} className="grid grid-cols-[18px_1fr] items-center gap-1">
                    <input type="checkbox" checked={r.enabled}
                      onChange={e => setQueryRows(prev => prev.map((row, idx) => idx === i ? { ...row, enabled: e.target.checked } : row))}
                      className="size-3"
                    />
                    <Input className="h-8 text-xs" placeholder={`${r.key}${r.required ? ' *' : ''}`}
                      value={r.value} aria-label={`Query 参数 ${r.key}`}
                      onChange={e => setQueryRows(prev => prev.map((row, idx) => idx === i ? { ...row, value: e.target.value } : row))}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between">
              <Label className="text-[11px] text-muted-foreground">Headers</Label>
              <Button type="button" size="icon-sm" variant="ghost" onClick={addHeader} title="添加 Header">
                <Plus className="size-3.5" />
              </Button>
            </div>
            <div className="space-y-1 mt-1">
              {headerRows.map((r, i) => (
                <div key={i} className="grid grid-cols-[18px_100px_1fr_28px] items-center gap-1">
                  <input type="checkbox" checked={r.enabled}
                    onChange={e => setHeaderRows(prev => prev.map((row, idx) => idx === i ? { ...row, enabled: e.target.checked } : row))}
                    className="size-3"
                  />
                  <Input className="h-8 text-xs" placeholder="Key" value={r.key} aria-label={`Header ${i + 1} 名称`}
                    onChange={e => setHeaderRows(prev => prev.map((row, idx) => idx === i ? { ...row, key: e.target.value } : row))}
                  />
                  <Input className="h-8 text-xs" placeholder="Value" value={r.value} aria-label={`Header ${i + 1} 值`}
                    onChange={e => setHeaderRows(prev => prev.map((row, idx) => idx === i ? { ...row, value: e.target.value } : row))}
                  />
                  <Button type="button" size="icon-sm" variant="ghost" className="text-destructive" onClick={() => removeHeader(i)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <Label className="text-[11px] text-muted-foreground">Body</Label>
            <Textarea className="font-mono text-xs mt-1 min-h-[120px]" value={body} onChange={e => setBody(e.target.value)} aria-label="请求 Body" />
          </div>

          <div>
            <Label className="text-[11px] text-muted-foreground">响应断言</Label>
            <Textarea className="font-mono text-xs mt-1 min-h-[96px]" value={assertions} onChange={e => setAssertions(e.target.value)} aria-label="响应断言" />
          </div>

          <Button size="sm" onClick={handleSend} disabled={!envId || loading} className="w-full" data-icon="inline-start">
            {loading ? <span className="inline-block size-3 border-2 border-current border-t-transparent rounded-full animate-spin mr-1" /> : <FlaskConical className="size-3.5" />}
            发送请求
          </Button>

          <ResponsePanel result={result} loading={loading} />
        </div>
      </div>
    </div>
  )
}

// normalizeJson, defaultAssertions, buildSampleBody imported from ./utils
// extractServiceName is specific to ApiDebugPanel (parses tags)

function extractServiceName(caseItem: any | null | undefined): string {
  if (!caseItem?.tags) return ''
  const tags = normalizeJson(caseItem.tags, [])
  if (!Array.isArray(tags)) return ''
  const serviceTag = tags.find((tag: any) => typeof tag === 'string' && tag.startsWith('service:'))
  return serviceTag ? serviceTag.replace(/^service:/, '') : ''
}
