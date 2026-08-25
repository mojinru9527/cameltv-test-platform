import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { toast } from 'sonner'
import {
  fetchReleaseBundle,
  updateReleaseBundle,
  fetchVersionChain,
  triggerVersionDiff,
  fetchRegressionScope,
  triggerRegression,
  fetchBundleCoverage,
  importBundleRequirement,
} from '@/api/releaseBundles'
import type { RegressionScopeResult, TriggerRegressionResult } from '@/api/releaseBundles'
import { fetchModuleTree } from '@/api/requirementModules'
import type { VersionDiffResult, Environment } from '@/types'
import { Button } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/ui'
import { Input } from '@/ui'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  ArrowLeft,
  Package,
  GitBranch,
  Layers,
  FileText,
  Settings,
  RefreshCw,
  Save,
  Monitor,
  Smartphone,
  X,
  Globe,
  Shield,
  type LucideIcon,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ProductionOperationDialog from '@/components/ProductionOperationDialog'
import ModuleTreeView from './components/ModuleTreeView'
import VersionChainTimeline from './components/VersionChainTimeline'
import DiffReviewPanel from './components/DiffReviewPanel'
import { useAuthStore } from '@/stores/auth'
import { fetchEnvironments } from '@/api/environment'

const PLATFORM_ICONS: Record<string, LucideIcon> = {
  APP: Smartphone,
  PC: Monitor,
  WEB: Globe,
  ADMIN: Shield,
}

const PLATFORM_LABELS: Record<string, string> = {
  APP: 'APP 端',
  PC: 'PC 端',
  WEB: 'WEB 端',
  ADMIN: '运营后台',
}

const STATUS_VARIANT: Record<string, { variant: 'secondary' | 'outline'; className?: string; label: string }> = {
  draft: { variant: 'secondary', className: 'border-status-warning-border bg-status-warning-muted text-status-warning', label: '草稿' },
  active: { variant: 'outline', className: 'border-status-success-border bg-status-success-muted text-status-success', label: '活跃' },
  archived: { variant: 'secondary', label: '已归档' },
}

export default function BundleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const bundleId = Number(id)
  const navigate = useNavigate()
  const canManage = useAuthStore((state) => state.hasPerm('knowledge:manage'))
  const canTriggerRegression = useAuthStore((state) => state.hasPerm('uitest:trigger'))
  const projects = useAuthStore((state) => state.projects)
  useDocumentTitle('发布包详情')

  const [tab, setTab] = useState('tree')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [diffing, setDiffing] = useState(false)
  const [diffResult, setDiffResult] = useState<VersionDiffResult | null>(null)

  // ── Edit form ──
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    client_version: '',
    admin_version: '',
    status: '',
    requirement_url: '',
    user_env_url: '',
    api_spec_url: '',
    admin_env_url: '',
    environment_id: undefined as number | null | undefined,
    parent_bundle_id: undefined as number | null | undefined,
  })
  const [importingRequirement, setImportingRequirement] = useState(false)

  // ── Data ──
  const {
    data: bundle,
    isLoading,
    isError,
    refetch,
    setData,
  } = useApi(() => fetchReleaseBundle(bundleId), [bundleId])

  const { data: versionChain } = useApi(
    () => fetchVersionChain(bundleId),
    [bundleId],
  )
  const { data: coverage, refetch: refetchCoverage } = useApi(
    (signal) => fetchBundleCoverage(bundleId, signal),
    [bundleId],
  )

  const { data: moduleTree } = useApi(
    () => fetchModuleTree(bundleId),
    [bundleId],
  )

  // ── Handlers ──
  const startEdit = () => {
    if (!bundle) return
    setEditForm({
      name: bundle.name,
      description: bundle.description,
      client_version: bundle.client_version,
      admin_version: bundle.admin_version,
      status: bundle.status,
      requirement_url: bundle.requirement_url ?? '',
      user_env_url: bundle.user_env_url ?? '',
      api_spec_url: bundle.api_spec_url ?? '',
      admin_env_url: bundle.admin_env_url ?? '',
      environment_id: bundle.environment_id ?? undefined,
      parent_bundle_id: bundle.parent_bundle_id ?? undefined,
    })
    setEditing(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateReleaseBundle(bundleId, {
        name: editForm.name,
        description: editForm.description,
        client_version: editForm.client_version,
        admin_version: editForm.admin_version,
        status: editForm.status,
        requirement_url: editForm.requirement_url,
        user_env_url: editForm.user_env_url,
        api_spec_url: editForm.api_spec_url,
        admin_env_url: editForm.admin_env_url,
        environment_id: editForm.environment_id ?? null,
        parent_bundle_id: editForm.parent_bundle_id ?? null,
      })
      setData(updated)
      setEditing(false)
      toast.success('已保存')
    } finally {
      setSaving(false)
    }
  }

  const handleDiff = async () => {
    if (!bundle?.parent_bundle_id) {
      toast.error('该发布包没有父版本，无法对比')
      return
    }
    setDiffing(true)
    setDiffResult(null)
    try {
      const result = await triggerVersionDiff(bundleId, {
        parent_bundle_id: bundle.parent_bundle_id,
        source_version: bundle.client_version,
      })
      setDiffResult(result)
      toast.success('差异对比完成')
    } finally {
      setDiffing(false)
    }
  }

  const handleImportRequirement = async () => {
    setImportingRequirement(true)
    try {
      const result = await importBundleRequirement(bundleId)
      toast.success(result.reused ? `已复用需求文档 #${result.document_id}` : `已创建需求文档 #${result.document_id}`)
      refetchCoverage()
    } catch {
      toast.error('导入需求失败，请确认需求地址可访问')
    } finally {
      setImportingRequirement(false)
    }
  }

  // ── Regression handlers (batch-34) ──
  const [regressionScope, setRegressionScope] = useState<RegressionScopeResult | null>(null)
  const [loadingScope, setLoadingScope] = useState(false)
  const [triggeringReg, setTriggeringReg] = useState(false)
  const [regressionDialogOpen, setRegressionDialogOpen] = useState(false)
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [regressionEnvironmentId, setRegressionEnvironmentId] = useState<number | undefined>()
  const regressionEnvironment = environments.find(environment => environment.id === regressionEnvironmentId)
  const isProductionEnvironment = regressionEnvironment?.is_production === true || regressionEnvironment?.env_type === 'prod'

  useEffect(() => {
    const controller = new AbortController()
    fetchEnvironments(controller.signal).then((rows) => {
      if (controller.signal.aborted) return
      setEnvironments(rows)
      const testEnvironment = rows.find(environment => environment.env_type === 'test' && !environment.is_production)
      setRegressionEnvironmentId(testEnvironment?.id)
    }).catch(() => {
      if (!controller.signal.aborted) setEnvironments([])
    })
    return () => controller.abort()
  }, [])

  const handleViewRegressionScope = async () => {
    setLoadingScope(true)
    try {
      const result = await fetchRegressionScope(bundleId)
      setRegressionScope(result)
      toast.success(`回归范围: ${result.total_regression_cases} 条测试用例`)
    } catch {
      toast.error('获取回归范围失败')
    } finally {
      setLoadingScope(false)
    }
  }

  const handleTriggerRegression = async () => {
    if (!regressionEnvironment) return
    setRegressionDialogOpen(false)
    setTriggeringReg(true)
    try {
      const result: TriggerRegressionResult = await triggerRegression(bundleId, {
        environment_id: regressionEnvironment.id,
        confirm_prod: isProductionEnvironment,
      })
      toast.success(`已触发 ${result.triggered} 个 UI 回归测试任务`)
      if (result.jobs?.length > 0) {
        result.jobs.forEach((j) => toast.info(`任务 #${j.job_id}: ${j.module}`))
      }
    } catch {
      toast.error('触发回归测试失败')
    } finally {
      setTriggeringReg(false)
    }
  }

  const handleRequestRegression = async () => {
    if (!regressionEnvironment) {
      toast.error('请先选择回归目标环境')
      return
    }
    if (regressionScope) {
      setRegressionDialogOpen(true)
      return
    }

    setLoadingScope(true)
    try {
      const result = await fetchRegressionScope(bundleId)
      setRegressionScope(result)
      setRegressionDialogOpen(true)
    } catch {
      toast.error('获取回归范围失败，未触发回归测试')
    } finally {
      setLoadingScope(false)
    }
  }

  // ── Render ──
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground text-sm">加载中...</div>
      </div>
    )
  }

  if (isError || !bundle) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <p className="text-muted-foreground">加载失败或发布包不存在</p>
        <Button variant="secondary" onClick={() => navigate('/release-bundles')}>
          <ArrowLeft className="size-4 mr-1" />
          返回列表
        </Button>
      </div>
    )
  }

  const totalNodes = moduleTree
    ? moduleTree.total_modules + moduleTree.total_pages + moduleTree.total_attachments
    : 0

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/release-bundles')} aria-label="返回发布包列表">
            <ArrowLeft className="size-5" aria-hidden="true" />
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="flex min-w-0 items-center gap-2 text-lg font-semibold">
              <Package className="size-5 text-primary" />
              {editing ? (
                <Input
                  className="h-11 min-w-0 w-full max-w-[400px] text-lg font-semibold"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                />
              ) : (
                bundle.name
              )}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              {bundle.client_version && (
                <code className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs">
                  <Smartphone className="size-3.5" aria-hidden="true" />
                  用户端 {bundle.client_version}
                </code>
              )}
              {bundle.admin_version && (
                <code className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs">
                  <Settings className="size-3.5" aria-hidden="true" />
                  运营后台 {bundle.admin_version}
                </code>
              )}
              <Badge
                variant={STATUS_VARIANT[bundle.status]?.variant ?? 'secondary'}
                className={cn('text-xs', STATUS_VARIANT[bundle.status]?.className)}
              >
                {STATUS_VARIANT[bundle.status]?.label ?? bundle.status}
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          {/* Regression actions (batch-34) */}
          {!editing && (
            <>
              {canTriggerRegression && (
                <Select
                  value={regressionEnvironmentId?.toString()}
                  onValueChange={(value) => setRegressionEnvironmentId(Number(value))}
                >
                  <SelectTrigger
                    className={cn('h-8 w-[180px] text-xs', isProductionEnvironment && 'border-status-danger-border')}
                    aria-label="回归目标环境"
                  >
                    <SelectValue placeholder="选择回归环境" />
                  </SelectTrigger>
                  <SelectContent>
                    {environments.map(environment => (
                      <SelectItem key={environment.id} value={environment.id.toString()}>
                        {environment.name}{environment.is_production || environment.env_type === 'prod' ? '（生产）' : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={handleViewRegressionScope}
                disabled={loadingScope}
              >
                {loadingScope ? <RefreshCw className="size-3.5 mr-1 animate-spin" /> : <Layers className="size-3.5 mr-1" />}
              {canManage && bundle.requirement_url && (
                <Button variant="secondary" size="sm" onClick={handleImportRequirement} disabled={importingRequirement}>
                  {importingRequirement ? <RefreshCw className="size-3.5 mr-1 animate-spin" /> : <FileText className="size-3.5 mr-1" />}
                  导入需求
                </Button>
              )}
                回归范围
              </Button>
              {canTriggerRegression && <Button
                size="sm"
                onClick={handleRequestRegression}
                disabled={triggeringReg || loadingScope}
              >
                {(triggeringReg || loadingScope) ? <RefreshCw className="size-3.5 mr-1 animate-spin" /> : <RefreshCw className="size-3.5 mr-1" />}
                触发UI回归
              </Button>}
            </>
          )}
          {editing ? (
            <>
              <Button variant="secondary" size="sm" onClick={() => setEditing(false)} disabled={saving}>
                取消
              </Button>
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saving && <RefreshCw className="size-4 mr-1 animate-spin" />}
                <Save className="size-4 mr-1" />
                保存
              </Button>
            </>
          ) : (
            canManage && <Button variant="ghost" size="sm" onClick={startEdit}>
              编辑
            </Button>
          )}
        </div>
      </div>

      {/* ── Stats cards ── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-2xl font-bold">{totalNodes}</div>
            <div className="text-xs text-muted-foreground">总节点数</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-2xl font-bold">{moduleTree?.total_modules ?? '-'}</div>
            <div className="text-xs text-muted-foreground">模块</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-2xl font-bold">{moduleTree?.total_pages ?? '-'}</div>
            <div className="text-xs text-muted-foreground">页面</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-2xl font-bold">{moduleTree?.total_attachments ?? '-'}</div>
            <div className="text-xs text-muted-foreground">附件</div>
          </CardContent>
        </Card>
      </div>

      {/* ── Regression scope result (batch-34) ── */}
      {regressionScope && (
        <Card className="border-status-info-border bg-status-info-muted">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Layers className="size-4 text-status-info" />
                UI 回归测试范围
              </CardTitle>
              <Button variant="ghost" size="icon-sm" onClick={() => setRegressionScope(null)} aria-label="关闭回归范围">
                <X className="size-4" aria-hidden="true" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div className="text-center">
                <div className="text-xl font-bold text-status-info">{regressionScope.changed_modules?.length || 0}</div>
                <div className="text-xs text-muted-foreground">变更模块</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-status-success">{regressionScope.total_regression_cases}</div>
                <div className="text-xs text-muted-foreground">回归用例</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-status-accent">{regressionScope.regression_summary?.length || 0}</div>
                <div className="text-xs text-muted-foreground">有测试覆盖的模块</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-status-warning">{regressionScope.client_version || '-'}</div>
                <div className="text-xs text-muted-foreground">目标版本</div>
              </div>
            </div>
            {regressionScope.regression_summary?.length > 0 && (
              <div className="space-y-1 max-h-[200px] overflow-y-auto">
                {regressionScope.regression_summary.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-muted/70">
                    <span className="font-medium">{s.module}</span>
                    <div className="flex items-center gap-3 text-muted-foreground">
                      <span>功能: {s.functional || 0}</span>
                      <span>API: {s.api || 0}</span>
                      <span>自动化: {s.automation || 0}</span>
                      <Badge tone="neutral" className="text-xs">覆盖率 {s.coverage_rate || 0}%</Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Edit form (expanded) ── */}
      {editing && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">编辑发布包信息</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label>描述</Label>
              <Textarea
                rows={2}
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              />
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>用户端版本</Label>
                  <Input
                    value={editForm.client_version}
                    onChange={(e) => setEditForm({ ...editForm, client_version: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>运营后台版本</Label>
                  <Input
                    value={editForm.admin_version}
                    onChange={(e) => setEditForm({ ...editForm, admin_version: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>状态</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
                  value={editForm.status}
                  onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                >
                  <option value="draft">草稿</option>
                  <option value="active">活跃</option>
                  <option value="archived">已归档</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>父版本（parent_bundle_id）</Label>
                <Input
                  type="number"
                  placeholder="父发布包 ID；留空表示独立版本（可用于版本差异对比）"
                  value={editForm.parent_bundle_id ?? ''}
                  onChange={(e) => setEditForm({
                    ...editForm,
                    parent_bundle_id: e.target.value === '' ? null : Number(e.target.value),
                  })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>账号/变量环境</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
                  value={editForm.environment_id?.toString() ?? ""}
                  onChange={(e) => setEditForm({ ...editForm, environment_id: e.target.value ? Number(e.target.value) : null })}
                >
                  <option value="">未绑定</option>
                  {environments.map((environment) => (
                    <option key={environment.id} value={environment.id.toString()}>{environment.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>需求地址</Label>
                <Input placeholder="PingCode/Confluence/蓝湖链接" value={editForm.requirement_url} onChange={(e) => setEditForm({ ...editForm, requirement_url: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>用户端地址</Label>
                <Input placeholder="https://user.example.com" value={editForm.user_env_url} onChange={(e) => setEditForm({ ...editForm, user_env_url: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>接口 OpenAPI/Swagger 地址</Label>
                <Input placeholder="https://api.example.com/openapi.json" value={editForm.api_spec_url} onChange={(e) => setEditForm({ ...editForm, api_spec_url: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>运营后台地址</Label>
                <Input placeholder="https://admin.example.com" value={editForm.admin_env_url} onChange={(e) => setEditForm({ ...editForm, admin_env_url: e.target.value })} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Tabs ── */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="tree">
            <Layers className="size-4 mr-1" />
            模块树 {moduleTree ? `(${totalNodes})` : ''}
          </TabsTrigger>
          <TabsTrigger value="version-chain">
            <GitBranch className="size-4 mr-1" />
            版本链 {versionChain ? `(${versionChain.length})` : ''}
          </TabsTrigger>
          <TabsTrigger value="diff">
            <FileText className="size-4 mr-1" />
            版本差异
          </TabsTrigger>
          <TabsTrigger value="coverage">
            <Shield className="size-4 mr-1" />
            三类型覆盖
          </TabsTrigger>
        </TabsList>

        {/* ── Module Tree Tab ── */}
        <TabsContent value="tree" className="mt-4">
          {moduleTree ? (
            <div className="space-y-4">
              {/* Platform legend */}
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {Object.entries(PLATFORM_LABELS).map(([key, label]) => {
                  const Icon = PLATFORM_ICONS[key] ?? Layers
                  return (
                    <span key={key} className="flex items-center gap-1">
                      <Icon className="size-3" />
                      {label}
                    </span>
                  )
                })}
              </div>
              <ModuleTreeView roots={moduleTree.roots} />
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Layers className="size-12 mx-auto mb-3 opacity-30" />
              <p>暂无模块树数据</p>
              <p className="text-xs mt-1">
                请先通过版本差异对比构建模块树，或从蓝湖证据包提取
              </p>
            </div>
          )}
        </TabsContent>

        {/* ── Version Chain Tab ── */}
        <TabsContent value="version-chain" className="mt-4">
          {versionChain && versionChain.length > 0 ? (
            <VersionChainTimeline chain={versionChain} currentId={bundleId} />
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <GitBranch className="size-12 mx-auto mb-3 opacity-30" />
              <p>暂无版本链</p>
              <p className="text-xs mt-1">该发布包为独立版本，无父版本关联</p>
            </div>
          )}
        </TabsContent>

        {/* ── Diff Tab ── */}
        {/* ── Coverage Tab (batch-167 Phase 0) ── */}
        <TabsContent value="coverage" className="mt-4">
          {tab === "coverage" && (<>
          {coverage ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
                <Card>
                  <CardContent className="p-3 text-center">
                    <div className={cn("text-2xl font-bold", coverage.gate_passed ? "text-status-success" : "text-status-warning")}>{coverage.covered_rate_percent}%</div>
                    <div className="text-xs text-muted-foreground">三类型用例覆盖（目标 60%）</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold">{coverage.covered_modules}/{coverage.total_modules}</div>
                    <div className="text-xs text-muted-foreground">已覆盖模块</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold">{coverage.executed_covered_rate_percent}%</div>
                    <div className="text-xs text-muted-foreground">API+UI 执行覆盖</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold">{coverage.p0p1_covered_modules}/{coverage.p0p1_modules}</div>
                    <div className="text-xs text-muted-foreground">P0/P1 已覆盖</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold">{coverage.client_version || "-"}</div>
                    <div className="text-xs text-muted-foreground">版本</div>
                  </CardContent>
                </Card>
              </div>
              {coverage.rows.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <p>尚无模块树数据</p>
                  <p className="text-xs mt-1">请先确认版本差异构建模块树，或导入需求文档</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs text-muted-foreground">
                        <th className="py-2 pr-2">模块</th>
                        <th className="py-2 px-2">P0/P1</th>
                        <th className="py-2 px-2 text-right">功能</th>
                        <th className="py-2 px-2 text-right">接口</th>
                        <th className="py-2 px-2 text-right">UI</th>
                        <th className="py-2 px-2 text-right">API/UI 已执行</th>
                        <th className="py-2 pl-2">缺口</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coverage.rows.map((row) => (
                        <tr key={row.module_id ?? row.name} className="border-b last:border-0">
                          <td className="py-2 pr-2 font-medium">{row.name}</td>
                          <td className="py-2 px-2">{row.is_p0p1 ? "P0/P1" : ""}</td>
                          <td className="py-2 px-2 text-right">{row.functional_count}</td>
                          <td className="py-2 px-2 text-right">{row.api_count}</td>
                          <td className="py-2 px-2 text-right">{row.ui_count}</td>
                          <td className="py-2 px-2 text-right">{row.api_executed > 0 && row.ui_executed > 0 ? "是" : "否"}</td>
                          <td className="py-2 pl-2">
                            {row.gap_types.length === 0 ? (
                              <Badge tone="success" className="text-xs">已覆盖</Badge>
                            ) : (
                              <span className="text-xs text-status-warning">{row.gap_types.join(", ")}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">加载覆盖数据中...</div>
          )}
          </>)}
        </TabsContent>
        <TabsContent value="diff" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span>版本差异对比</span>
                <div className="flex items-center gap-2">
                  {canManage && <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleDiff}
                    disabled={diffing || !bundle.parent_bundle_id}
                  >
                    {diffing && <RefreshCw className="size-4 mr-1 animate-spin" />}
                    触发对比
                  </Button>}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!bundle.parent_bundle_id ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  该发布包没有父版本。请先编辑发布包，关联
                  <code className="text-xs bg-muted px-1 rounded">parent_bundle_id</code>
                  建立版本链后再对比。
                </p>
              ) : diffResult ? (
                <DiffReviewPanel
                  bundleId={bundleId}
                  diffResult={diffResult}
                  onConfirm={() => {
                    setDiffResult(null)
                    refetch()
                  }}
                />
              ) : (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  点击「触发对比」比较当前版本与父版本的模块/页面变化
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ProductionOperationDialog
        open={regressionDialogOpen}
        onOpenChange={setRegressionDialogOpen}
        project={projects.find(project => project.id === bundle.project_id)?.name || `项目 #${bundle.project_id}`}
        environment={regressionEnvironment?.name || '未选择环境'}
        baseUrl={regressionEnvironment?.base_url || '未配置'}
        operation={`触发发布包「${bundle.name}」UI 回归`}
        classification="write"
        affectedCount={regressionScope?.total_regression_cases ?? 0}
        isProduction={isProductionEnvironment}
        pending={triggeringReg}
        onConfirm={handleTriggerRegression}
      />
    </div>
  )
}





