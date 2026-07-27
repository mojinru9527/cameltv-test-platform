import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  fetchReleaseBundle,
  updateReleaseBundle,
  fetchVersionChain,
  triggerVersionDiff,
  fetchRegressionScope,
  triggerRegression,
} from '@/api/releaseBundles'
import type { RegressionScopeResult, TriggerRegressionResult } from '@/api/releaseBundles'
import { fetchModuleTree } from '@/api/requirementModules'
import type {
  ReleaseBundleOut,
  ReleaseBundleVersionChain,
  ModuleTreeResponse,
  VersionDiffResult,
} from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Monitor,
  Smartphone,
  Globe,
  Shield,
  type LucideIcon,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AsyncState } from '@/components/state'
import ModuleTreeView from './components/ModuleTreeView'
import VersionChainTimeline from './components/VersionChainTimeline'
import DiffReviewPanel from './components/DiffReviewPanel'

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
  draft: { variant: 'secondary', className: 'border-yellow-200 bg-yellow-50 text-yellow-700', label: '草稿' },
  active: { variant: 'outline', className: 'border-green-200 bg-green-50 text-green-700', label: '活跃' },
  archived: { variant: 'secondary', label: '已归档' },
}

export default function BundleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const bundleId = Number(id)
  const navigate = useNavigate()
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
  })

  // ── Data ──
  const {
    data: bundle,
    isLoading,
    isError,
    refetch,
    setData,
  } = useApi((signal) => fetchReleaseBundle(bundleId), [bundleId])

  const { data: versionChain } = useApi(
    (signal) => fetchVersionChain(bundleId),
    [bundleId],
  )

  const { data: moduleTree } = useApi(
    (signal) => fetchModuleTree(bundleId),
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

  // ── Regression handlers (batch-34) ──
  const [regressionScope, setRegressionScope] = useState<RegressionScopeResult | null>(null)
  const [loadingScope, setLoadingScope] = useState(false)
  const [triggeringReg, setTriggeringReg] = useState(false)

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
    setTriggeringReg(true)
    try {
      const result: TriggerRegressionResult = await triggerRegression(bundleId)
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
        <Button variant="outline" onClick={() => navigate('/release-bundles')}>
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
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/release-bundles')}>
            <ArrowLeft className="size-5" />
          </Button>
          <div>
            <h1 className="text-lg font-semibold flex items-center gap-2">
              <Package className="size-5 text-primary" />
              {editing ? (
                <Input
                  className="h-8 w-[400px] text-lg font-semibold"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                />
              ) : (
                bundle.name
              )}
            </h1>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              {bundle.client_version && (
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                  📱 用户端 {bundle.client_version}
                </code>
              )}
              {bundle.admin_version && (
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                  ⚙️ 运营后台 {bundle.admin_version}
                </code>
              )}
              <Badge
                variant={STATUS_VARIANT[bundle.status]?.variant ?? 'secondary'}
                className={cn('text-[11px]', STATUS_VARIANT[bundle.status]?.className)}
              >
                {STATUS_VARIANT[bundle.status]?.label ?? bundle.status}
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Regression actions (batch-34) */}
          {!editing && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleViewRegressionScope}
                disabled={loadingScope}
              >
                {loadingScope ? <RefreshCw className="size-3.5 mr-1 animate-spin" /> : <Layers className="size-3.5 mr-1" />}
                回归范围
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleTriggerRegression}
                disabled={triggeringReg}
              >
                {triggeringReg ? <RefreshCw className="size-3.5 mr-1 animate-spin" /> : <RefreshCw className="size-3.5 mr-1" />}
                触发UI回归
              </Button>
            </>
          )}
          {editing ? (
            <>
              <Button variant="outline" size="sm" onClick={() => setEditing(false)} disabled={saving}>
                取消
              </Button>
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saving && <RefreshCw className="size-4 mr-1 animate-spin" />}
                <Save className="size-4 mr-1" />
                保存
              </Button>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={startEdit}>
              编辑
            </Button>
          )}
        </div>
      </div>

      {/* ── Stats cards ── */}
      <div className="grid grid-cols-4 gap-3">
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
        <Card className="border-blue-200 bg-blue-50/50">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Layers className="size-4 text-blue-600" />
                UI 回归测试范围
              </CardTitle>
              <Button variant="ghost" size="icon-sm" onClick={() => setRegressionScope(null)}>
                <span className="text-xs">✕</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-3 mb-3">
              <div className="text-center">
                <div className="text-xl font-bold text-blue-700">{regressionScope.changed_modules?.length || 0}</div>
                <div className="text-xs text-muted-foreground">变更模块</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-green-700">{regressionScope.total_regression_cases}</div>
                <div className="text-xs text-muted-foreground">回归用例</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-purple-700">{regressionScope.regression_summary?.length || 0}</div>
                <div className="text-xs text-muted-foreground">有测试覆盖的模块</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-amber-700">{regressionScope.client_version || '-'}</div>
                <div className="text-xs text-muted-foreground">目标版本</div>
              </div>
            </div>
            {regressionScope.regression_summary?.length > 0 && (
              <div className="space-y-1 max-h-[200px] overflow-y-auto">
                {regressionScope.regression_summary.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-white/70">
                    <span className="font-medium">{s.module}</span>
                    <div className="flex items-center gap-3 text-muted-foreground">
                      <span>功能: {s.functional || 0}</span>
                      <span>API: {s.api || 0}</span>
                      <span>自动化: {s.automation || 0}</span>
                      <Badge variant="outline" className="text-[10px]">覆盖率 {s.coverage_rate || 0}%</Badge>
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
          <CardContent className="grid grid-cols-2 gap-4">
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
        <TabsContent value="diff" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span>版本差异对比</span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleDiff}
                    disabled={diffing || !bundle.parent_bundle_id}
                  >
                    {diffing && <RefreshCw className="size-4 mr-1 animate-spin" />}
                    触发对比
                  </Button>
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
    </div>
  )
}
