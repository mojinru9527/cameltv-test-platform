import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Play, Save, Plus, Trash2, Code2, Loader2 } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import PageHeader from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'

const STORAGE_KEY = 'cameltv-api-test-examples'
const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as const

const METHOD_BADGE_CLASSES: Record<string, string> = {
  GET: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  POST: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  PUT: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  PATCH: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  DELETE: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

const DEFAULT_EXAMPLES: ApiExample[] = [
  { name: '健康检查', method: 'GET', url: '/health', body: '', headers: '' },
  { name: '当前用户', method: 'GET', url: '/api/v1/auth/me', body: '', headers: '' },
  { name: '测试用例列表', method: 'GET', url: '/api/v1/test-cases?page=1&page_size=10', body: '', headers: '' },
]

const apiExampleSchema = z.object({
  name: z.string().min(1, '请输入名称'),
  method: z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']),
  url: z.string().min(1, '请输入 URL'),
  headers: z.string().optional(),
  body: z.string().optional(),
})

type ApiExample = z.infer<typeof apiExampleSchema>

export default function ApiTestPage() {
  const token = useAuthStore((state) => state.token)
  const currentProjectId = useAuthStore((state) => state.currentProjectId)
  const [examples, setExamples] = useState<ApiExample[]>(DEFAULT_EXAMPLES)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<ApiExample>({
    resolver: zodResolver(apiExampleSchema),
    defaultValues: DEFAULT_EXAMPLES[0],
  })

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        setExamples(JSON.parse(saved))
      } catch { /* ignore parse errors */ }
    }
    form.reset(DEFAULT_EXAMPLES[0])
  }, [form])

  const stats = useMemo(() => {
    const byMethod = examples.reduce<Record<string, number>>((acc, item) => {
      acc[item.method] = (acc[item.method] || 0) + 1
      return acc
    }, {})
    return { total: examples.length, byMethod }
  }, [examples])

  const persist = (items: ApiExample[]) => {
    setExamples(items)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }

  const parseJson = (value?: string) => {
    if (!value?.trim()) return undefined
    return JSON.parse(value)
  }

  const run = async () => {
    const valid = await form.trigger()
    if (!valid) return
    const values = form.getValues()
    setLoading(true)
    setResult(null)
    const started = performance.now()
    try {
      const headers: Record<string, string> = {
        Accept: 'application/json',
        ...(parseJson(values.headers) || {}),
      }
      if (token) headers.Authorization = `Bearer ${token}`
      if (currentProjectId) headers['X-Project-Id'] = String(currentProjectId)

      const hasBody = !['GET', 'DELETE'].includes(values.method)
      if (hasBody) headers['Content-Type'] = 'application/json'
      const response = await fetch(values.url, {
        method: values.method,
        headers,
        body: hasBody && values.body?.trim() ? values.body : undefined,
      })
      const text = await response.text()
      let data: unknown = text
      try {
        data = text ? JSON.parse(text) : null
      } catch {
        data = text
      }
      setResult({
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
        duration: Math.round(performance.now() - started),
        data,
      })
    } catch (error: any) {
      setResult({ ok: false, status: 'ERR', statusText: error.message, duration: Math.round(performance.now() - started) })
    } finally {
      setLoading(false)
    }
  }

  const saveExample = async () => {
    const valid = await form.trigger()
    if (!valid) return
    const values = form.getValues()
    const next = [values, ...examples.filter((item) => item.name !== values.name)].slice(0, 20)
    persist(next)
    toast.success('已保存接口用例')
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader title="接口测试" description="调试后端接口、复用登录态并保存常用请求。">
        <Button variant="outline" onClick={saveExample} data-icon="inline-start">
          <Save />
          保存
        </Button>
        <Button onClick={run} disabled={loading} data-icon="inline-start">
          {loading ? (
            <Loader2 className="animate-spin" />
          ) : (
            <Play />
          )}
          发送
        </Button>
      </PageHeader>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Code2 className="size-4" />
              <span>已保存请求</span>
            </div>
            <div className="text-2xl font-semibold mt-1">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-sm text-muted-foreground">当前项目</div>
            <div className="text-2xl font-semibold mt-1">{currentProjectId || '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-sm text-muted-foreground">登录态</div>
            <div className="text-2xl font-semibold mt-1">{token ? '已注入' : '未登录'}</div>
          </CardContent>
        </Card>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Request form - takes 2/3 on large screens */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>请求配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Row 1: name, method, url */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                <div className="md:col-span-4">
                  <label className="text-sm font-medium mb-1.5 block">
                    名称 <span className="text-destructive">*</span>
                  </label>
                  <Input
                    placeholder="例如：测试用例列表"
                    {...form.register('name')}
                    aria-invalid={!!form.formState.errors.name}
                  />
                  {form.formState.errors.name && (
                    <p className="text-xs text-destructive mt-1">{form.formState.errors.name.message}</p>
                  )}
                </div>
                <div className="md:col-span-3">
                  <label className="text-sm font-medium mb-1.5 block">
                    方法 <span className="text-destructive">*</span>
                  </label>
                  <Select
                    value={form.watch('method')}
                    onValueChange={(v) => form.setValue('method', v as ApiExample['method'], { shouldValidate: true })}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="选择方法" />
                    </SelectTrigger>
                    <SelectContent>
                      {METHODS.map((method) => (
                        <SelectItem key={method} value={method}>
                          {method}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {form.formState.errors.method && (
                    <p className="text-xs text-destructive mt-1">{form.formState.errors.method.message}</p>
                  )}
                </div>
                <div className="md:col-span-5">
                  <label className="text-sm font-medium mb-1.5 block">
                    URL <span className="text-destructive">*</span>
                  </label>
                  <Input
                    placeholder="/api/v1/test-cases?page=1&page_size=10"
                    {...form.register('url')}
                    aria-invalid={!!form.formState.errors.url}
                  />
                  {form.formState.errors.url && (
                    <p className="text-xs text-destructive mt-1">{form.formState.errors.url.message}</p>
                  )}
                </div>
              </div>

              {/* Headers */}
              <div>
                <label className="text-sm font-medium mb-1.5 block">额外 Headers (JSON)</label>
                <Textarea
                  rows={3}
                  placeholder='{"X-Debug":"1"}'
                  {...form.register('headers')}
                />
              </div>

              {/* Body */}
              <div>
                <label className="text-sm font-medium mb-1.5 block">请求体 (JSON)</label>
                <Textarea
                  rows={8}
                  placeholder='{"title":"示例用例"}'
                  {...form.register('body')}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right sidebar - takes 1/3 on large screens */}
        <div className="space-y-4">
          {/* Saved examples list */}
          <Card>
            <CardHeader>
              <CardTitle>请求库</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y">
                {examples.map((item) => (
                  <li key={item.name} className="flex items-center gap-2 px-4 py-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge className={METHOD_BADGE_CLASSES[item.method] || ''}>{item.method}</Badge>
                        <span className="text-sm font-medium truncate">{item.name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{item.url}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        onClick={() => form.reset(item)}
                        title="填入表单"
                      >
                        <Plus />
                      </Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        onClick={() => persist(examples.filter((example) => example.name !== item.name))}
                        className="text-destructive hover:text-destructive"
                        title="删除"
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Method distribution */}
          <Card>
            <CardHeader>
              <CardTitle>方法分布</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {METHODS.map((method) => (
                  <Badge key={method} variant="outline">
                    {method}: {stats.byMethod[method] || 0}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Response */}
      <Card>
        <CardHeader>
          <CardTitle>响应结果</CardTitle>
        </CardHeader>
        <CardContent>
          {result ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={result.ok ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}>
                  {result.status} {result.statusText}
                </Badge>
                <Badge variant="outline">{result.duration} ms</Badge>
              </div>
              <pre className="text-sm whitespace-pre-wrap break-all bg-muted rounded-lg p-4 max-h-96 overflow-auto">
                {JSON.stringify(result.data ?? result, null, 2)}
              </pre>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">发送请求后将在这里展示响应。</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
