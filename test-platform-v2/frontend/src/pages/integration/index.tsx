import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'
import {
  Link2, Plus, RefreshCw, Settings, Trash2, Wifi, WifiOff,
  GitBranch, FileCheck, Server, Monitor, ArrowRight, Layers,
} from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import {
  fetchIntegrations, createIntegration, updateIntegration, deleteIntegration,
  testConnection, syncNow, fetchSyncLogs,
} from '@/api/integration'
import { fetchRequirements } from '@/api/requirement'
import { fetchTestCases } from '@/api/testcase'
import type { IntegrationConfig, SyncLog, RequirementDocument } from '@/types'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

// ── Form schema ──

const formSchema = z.object({
  name: z.string().min(1, '名称不能为空'),
  provider_type: z.enum(['jira', 'tapd']),
  base_url: z.string().min(1, 'Base URL 不能为空'),
  email: z.string().optional(),
  api_token: z.string().optional(),
  api_user: z.string().optional(),
  api_password: z.string().optional(),
  project_key: z.string().optional(),
  workspace_id: z.string().optional(),
  sync_direction: z.string().default('bidirectional'),
  sync_interval_minutes: z.coerce.number().min(0).default(0),
  enabled: z.boolean().default(true),
})

type FormValues = z.infer<typeof formSchema>

// ── Provider badge ──

const providerBadge = (t: string) => {
  const map: Record<string, { label: string; className: string }> = {
    jira: { label: 'Jira', className: 'bg-blue-100 text-blue-800' },
    tapd: { label: 'TAPD', className: 'bg-orange-100 text-orange-800' },
  }
  const m = map[t] || { label: t, className: 'bg-slate-100' }
  return <Badge className={m.className} variant="outline">{m.label}</Badge>
}

// ── Status icons ──

const StatusIcon = ({ status }: { status: string }) => {
  if (status === 'success') return <span className="text-green-600" title="成功">✓</span>
  if (status === 'failed') return <span className="text-red-600" title="失败">✗</span>
  return <span className="text-yellow-600" title="跳过">→</span>
}

// ── Component ──

export default function IntegrationPage() {
  useDocumentTitle('集成管理')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [integrations, setIntegrations] = useState<IntegrationConfig[]>([])
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<IntegrationConfig | null>(null)
  const [testing, setTesting] = useState(false)
  const [syncing, setSyncing] = useState<number | null>(null)
  const [logsOpen, setLogsOpen] = useState<number | null>(null)
  const [logs, setLogs] = useState<SyncLog[]>([])

  // ── Linkage tracking (batch-34) ──
  const [linkageData, setLinkageData] = useState<{
    totalRequirements: number
    totalCases: number
    linkedCases: number
    reqsWithCases: number
    apiEndpoints: number
    uiScripts: number
  }>({ totalRequirements: 0, totalCases: 0, linkedCases: 0, reqsWithCases: 0, apiEndpoints: 0, uiScripts: 0 })
  const [loadingLinkage, setLoadingLinkage] = useState(false)

  // fetchIntegrations returns the promise directly; useApi's object contract
  // doesn't fit this "call then setState" usage, so use a plain callback.
  const load = useCallback(() => fetchIntegrations(), [])

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '', provider_type: 'jira', base_url: '',
      email: '', api_token: '', api_user: '', api_password: '',
      project_key: '', workspace_id: '',
      sync_direction: 'bidirectional', sync_interval_minutes: 0, enabled: true,
    },
  })

  const providerType = form.watch('provider_type')

  const refresh = useCallback(() => {
    load().then((r: any) => setIntegrations(r?.items || [])).catch(() => {})
  }, [load])

  useEffect(() => { refresh() }, [refresh])

  // ── Load linkage data ──
  useEffect(() => {
    setLoadingLinkage(true)
    Promise.all([
      fetchRequirements().catch(() => [] as RequirementDocument[]),
      fetchTestCases({ page: 1, page_size: 1 }).catch(() => ({ total: 0 })),
    ]).then(([reqs, casesResult]) => {
      const caseData = casesResult as { total: number }
      setLinkageData({
        totalRequirements: (reqs as RequirementDocument[]).length,
        totalCases: caseData.total || 0,
        linkedCases: (reqs as RequirementDocument[]).reduce((sum, r) => sum + (r.imported_count || 0), 0),
        reqsWithCases: (reqs as RequirementDocument[]).filter(r => (r.imported_count || 0) > 0).length,
        apiEndpoints: 0,  // would come from apitest API
        uiScripts: 0,     // would come from uitest API
      })
    }).catch(() => {}).finally(() => setLoadingLinkage(false))
  }, [])

  // ── Form actions ──

  const openCreate = () => {
    setEditing(null)
    form.reset({
      name: '', provider_type: 'jira', base_url: '',
      email: '', api_token: '', api_user: '', api_password: '',
      project_key: '', workspace_id: '',
      sync_direction: 'bidirectional', sync_interval_minutes: 0, enabled: true,
    })
    setDrawer(true)
  }

  const openEdit = (r: IntegrationConfig) => {
    setEditing(r)
    form.reset({
      name: r.name, provider_type: r.provider_type as 'jira' | 'tapd', base_url: r.base_url,
      email: '', api_token: '', api_user: '', api_password: '',
      project_key: '', workspace_id: '',
      sync_direction: r.sync_direction,
      sync_interval_minutes: r.sync_interval_minutes,
      enabled: r.enabled,
    })
    setDrawer(true)
  }

  const handleSave = async (values: FormValues) => {
    // Build auth JSON from provider-specific fields
    let authJson = '{}'
    if (values.provider_type === 'jira') {
      const extra: Record<string, string> = {}
      if (values.project_key) extra.project_key = values.project_key
      authJson = JSON.stringify({ email: values.email || '', api_token: values.api_token || '', ...extra })
    } else {
      const extra: Record<string, string> = {}
      if (values.workspace_id) extra.workspace_id = values.workspace_id
      authJson = JSON.stringify({ api_user: values.api_user || '', api_password: values.api_password || '', ...extra })
    }

    const payload = {
      name: values.name,
      provider_type: values.provider_type,
      base_url: values.base_url,
      auth_json: authJson,
      sync_direction: values.sync_direction,
      sync_interval_minutes: values.sync_interval_minutes,
      enabled: values.enabled,
    }

    if (editing) {
      await updateIntegration(editing.id, payload)
      toast.success('集成配置已更新')
    } else {
      await createIntegration(payload)
      toast.success('集成配置已创建')
    }
    setDrawer(false)
    refresh()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此集成配置？')) return
    await deleteIntegration(id)
    toast.success('已删除')
    refresh()
  }

  const handleTest = async () => {
    const values = form.getValues()
    let authJson = '{}'
    if (values.provider_type === 'jira') {
      authJson = JSON.stringify({ email: values.email || '', api_token: values.api_token || '' })
    } else {
      authJson = JSON.stringify({ api_user: values.api_user || '', api_password: values.api_password || '' })
    }

    setTesting(true)
    try {
      const r = await testConnection({
        provider_type: values.provider_type,
        base_url: values.base_url,
        auth_json: authJson,
      })
      if (r.success) {
        toast.success(r.message || '连接成功')
      } else {
        toast.error(r.message || '连接失败')
      }
    } catch (e: any) {
      toast.error(e?.message || '测试连接失败')
    } finally {
      setTesting(false)
    }
  }

  const handleSync = async (id: number) => {
    setSyncing(id)
    try {
      const r = await syncNow(id)
      toast.success(`同步完成: 推送 ${r.pushed}, 拉取 ${r.pulled}, 错误 ${r.errors}`)
      refresh()
    } catch (e: any) {
      toast.error(e?.message || '同步失败')
    } finally {
      setSyncing(null)
    }
  }

  const openLogs = async (id: number) => {
    setLogsOpen(id)
    try {
      const r = await fetchSyncLogs(id, { page_size: 50 })
      setLogs(r?.items || [])
    } catch {
      setLogs([])
    }
  }

  // ── Render ──

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">集成配置</h1>
          <p className="text-sm text-muted-foreground mt-1">
            管理 Jira / TAPD 外部缺陷同步连接
          </p>
        </div>
        {hasPerm('integration:manage') && (
          <Button onClick={openCreate}><Plus className="size-4 mr-1" />新建集成</Button>
        )}
      </div>

      {/* ── Linkage Tracking Panel (batch-34) ── */}
      <Card className="border-blue-200 bg-gradient-to-r from-blue-50/50 to-white">
        <CardContent className="pt-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <GitBranch className="size-5 text-blue-600" />
              <h2 className="text-lg font-semibold">模块联动追踪</h2>
              <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700 text-xs">需求 → 用例 → 执行</Badge>
            </div>
            <Button variant="outline" size="sm" onClick={() => {
              setLoadingLinkage(true)
              Promise.all([
                fetchRequirements().catch(() => [] as RequirementDocument[]),
                fetchTestCases({ page: 1, page_size: 1 }).catch(() => ({ total: 0 })),
              ]).then(([reqs, casesResult]) => {
                const caseData = casesResult as { total: number }
                setLinkageData({
                  totalRequirements: (reqs as RequirementDocument[]).length,
                  totalCases: caseData.total || 0,
                  linkedCases: (reqs as RequirementDocument[]).reduce((sum, r) => sum + (r.imported_count || 0), 0),
                  reqsWithCases: (reqs as RequirementDocument[]).filter(r => (r.imported_count || 0) > 0).length,
                  apiEndpoints: linkageData.apiEndpoints,
                  uiScripts: linkageData.uiScripts,
                })
              }).catch(() => {}).finally(() => setLoadingLinkage(false))
            }} disabled={loadingLinkage}>
              <RefreshCw className={cn('size-3.5 mr-1', loadingLinkage && 'animate-spin')} />
              刷新
            </Button>
          </div>

          {/* Linkage flow */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <div className="flex items-center gap-1.5 bg-blue-100 rounded-full px-3 py-1">
              <FileCheck className="size-3.5 text-blue-600" />
              <span className="font-medium">{linkageData.totalRequirements}</span>
              <span className="text-muted-foreground">需求</span>
            </div>
            <ArrowRight className="size-4 text-muted-foreground" />
            <div className="flex items-center gap-1.5 bg-green-100 rounded-full px-3 py-1">
              <Layers className="size-3.5 text-green-600" />
              <span className="font-medium">{linkageData.totalCases}</span>
              <span className="text-muted-foreground">用例</span>
            </div>
            <ArrowRight className="size-4 text-muted-foreground" />
            <div className="flex items-center gap-1.5 bg-purple-100 rounded-full px-3 py-1">
              <Server className="size-3.5 text-purple-600" />
              <span className="font-medium">{linkageData.apiEndpoints || '-'}</span>
              <span className="text-muted-foreground">API端点</span>
            </div>
            <ArrowRight className="size-4 text-muted-foreground" />
            <div className="flex items-center gap-1.5 bg-amber-100 rounded-full px-3 py-1">
              <Monitor className="size-3.5 text-amber-600" />
              <span className="font-medium">{linkageData.uiScripts || '-'}</span>
              <span className="text-muted-foreground">UI脚本</span>
            </div>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">用例关联率</span>
                <span className="font-medium">
                  {linkageData.totalRequirements > 0
                    ? Math.round((linkageData.linkedCases / Math.max(linkageData.totalCases, 1)) * 100)
                    : 0}%
                </span>
              </div>
              <Progress
                value={linkageData.totalCases > 0
                  ? Math.round((linkageData.linkedCases / linkageData.totalCases) * 100)
                  : 0}
                className="h-2"
              />
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">需求覆盖率</span>
                <span className="font-medium">
                  {linkageData.totalRequirements > 0
                    ? Math.round((linkageData.reqsWithCases / linkageData.totalRequirements) * 100)
                    : 0}%
                </span>
              </div>
              <Progress
                value={linkageData.totalRequirements > 0
                  ? Math.round((linkageData.reqsWithCases / linkageData.totalRequirements) * 100)
                  : 0}
                className="h-2 [&>div]:bg-green-500"
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <FileCheck className="size-3.5" />
              <span>已联动用例: <strong className="text-foreground">{linkageData.linkedCases}</strong></span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <GitBranch className="size-3.5" />
              <span>模块联动状态: <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700 text-[10px]">运行中</Badge></span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Section Divider ── */}
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-medium text-muted-foreground">外部集成配置</h3>
        <div className="flex-1 border-t" />
      </div>

      {/* ── List ── */}
      {integrations.length === 0 ? (
        <Card className="p-12 text-center text-muted-foreground">
          <Settings className="size-12 mx-auto mb-3 opacity-30" />
          <p>暂无集成配置</p>
          {hasPerm('integration:manage') && (
            <Button variant="link" onClick={openCreate}>立即创建</Button>
          )}
        </Card>
      ) : (
        <div className="grid gap-4">
          {integrations.map((r) => (
            <Card key={r.id} className="p-5 flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex items-center gap-2">
                  <Link2 className="size-4 text-muted-foreground shrink-0" />
                  <span className="font-semibold truncate">{r.name}</span>
                  {providerBadge(r.provider_type)}
                  {r.enabled ? (
                    <Wifi className="size-3.5 text-green-600" />
                  ) : (
                    <WifiOff className="size-3.5 text-muted-foreground" />
                  )}
                </div>
                <p className="text-xs text-muted-foreground truncate">{r.base_url}</p>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>方向: {r.sync_direction === 'bidirectional' ? '双向' : r.sync_direction === 'push_only' ? '仅推送' : '仅拉取'}</span>
                  {r.sync_interval_minutes > 0 && (
                    <span>自动: 每 {r.sync_interval_minutes} 分钟</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                {hasPerm('integration:sync') && (
                  <Button
                    variant="outline" size="sm"
                    disabled={syncing === r.id}
                    onClick={() => handleSync(r.id)}
                  >
                    <RefreshCw className={cn('size-3.5 mr-1', syncing === r.id && 'animate-spin')} />
                    同步
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => openLogs(r.id)}>日志</Button>
                {hasPerm('integration:manage') && (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>编辑</Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)}>
                      <Trash2 className="size-3.5 text-red-500" />
                    </Button>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* ── Create / Edit Dialog ── */}
      <Dialog open={drawer} onOpenChange={setDrawer}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? '编辑集成' : '新建集成'}</DialogTitle>
            <DialogDescription>
              配置 Jira 或 TAPD 连接信息。凭据将加密存储。
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={form.handleSubmit(handleSave)} className="space-y-4">
            {/* Basic */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>名称 *</Label>
                <Input placeholder="项目Jira连接" {...form.register('name')} />
              </div>
              <div className="space-y-1">
                <Label>类型 *</Label>
                <Select value={providerType} onValueChange={(v) => form.setValue('provider_type', v as 'jira' | 'tapd')}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="jira">Jira Cloud</SelectItem>
                    <SelectItem value="tapd">TAPD</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label>Base URL *</Label>
              <Input placeholder={providerType === 'jira' ? 'https://your-domain.atlassian.net' : 'https://api.tapd.cn'} {...form.register('base_url')} />
            </div>

            {/* Provider-specific auth fields */}
            {providerType === 'jira' ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>Email</Label>
                  <Input placeholder="your-email@example.com" {...form.register('email')} />
                </div>
                <div className="space-y-1">
                  <Label>API Token</Label>
                  <Input type="password" placeholder="Jira API Token" {...form.register('api_token')} />
                </div>
                <div className="space-y-1">
                  <Label>Project Key</Label>
                  <Input placeholder="PROJ (Jira项目键)" {...form.register('project_key')} />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>API User</Label>
                  <Input placeholder="TAPD API 用户名" {...form.register('api_user')} />
                </div>
                <div className="space-y-1">
                  <Label>API Password</Label>
                  <Input type="password" placeholder="TAPD API 密码" {...form.register('api_password')} />
                </div>
                <div className="space-y-1">
                  <Label>Workspace ID</Label>
                  <Input placeholder="TAPD 项目 ID" {...form.register('workspace_id')} />
                </div>
              </div>
            )}

            {/* Sync settings */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label>同步方向</Label>
                <Select value={form.watch('sync_direction')} onValueChange={(v) => form.setValue('sync_direction', v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bidirectional">双向同步</SelectItem>
                    <SelectItem value="push_only">仅推送</SelectItem>
                    <SelectItem value="pull_only">仅拉取</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>自动同步 (分钟)</Label>
                <Input type="number" min={0} placeholder="0=禁用" {...form.register('sync_interval_minutes')} />
              </div>
              <div className="space-y-1 flex items-end pb-1">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" {...form.register('enabled')} className="rounded" />
                  启用
                </label>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={testing}>{editing ? '保存' : '创建'}</Button>
              <Button type="button" variant="outline" disabled={testing} onClick={handleTest}>
                {testing ? '测试中...' : '测试连接'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── Sync Logs Dialog ── */}
      <Dialog open={logsOpen !== null} onOpenChange={() => setLogsOpen(null)}>
        <DialogContent className="max-w-2xl max-h-[70vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>同步日志</DialogTitle>
          </DialogHeader>
          {logs.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">暂无同步记录</p>
          ) : (
            <div className="space-y-2">
              {logs.map((l) => (
                <div key={l.id} className="flex items-start gap-3 p-3 bg-muted/40 rounded text-sm">
                  <StatusIcon status={l.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">{l.direction === 'push' ? '推送' : '拉取'}</Badge>
                      <span className="font-mono text-xs">{l.external_id || '-'}</span>
                      <span className="text-xs text-muted-foreground">
                        {l.created_at ? new Date(l.created_at).toLocaleString('zh-CN') : ''}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 truncate">{l.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
