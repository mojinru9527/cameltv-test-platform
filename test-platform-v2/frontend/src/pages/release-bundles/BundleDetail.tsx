import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  fetchReleaseBundle,
  updateReleaseBundle,
  fetchVersionChain,
  triggerVersionDiff,
  confirmVersionDiff,
} from '@/api/releaseBundles'
import { fetchModuleTree } from '@/api/requirementModules'
import type {
  ReleaseBundleOut,
  ReleaseBundleVersionChain,
  ModuleTreeResponse,
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
  const [diffResult, setDiffResult] = useState<Record<string, unknown> | null>(null)

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

  const handleConfirmDiff = async () => {
    try {
      const result = await confirmVersionDiff(bundleId)
      toast.success(`模块树已构建：${result.module_count} 个模块，${result.page_count} 个页面`)
      refetch()
      setDiffResult(null)
    } catch {
      // handled by interceptor
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
                  {diffResult && (
                    <Button size="sm" onClick={handleConfirmDiff}>
                      确认差异并构建模块树
                    </Button>
                  )}
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
                <DiffResultView result={diffResult} />
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

// ── Diff Result Sub-component ──

function DiffResultView({ result }: { result: Record<string, unknown> }) {
  const summary = (result.warnings as string[]) ?? []
  const newMods = (result.new_modules as Array<Record<string, unknown>>) ?? []
  const modMods = (result.modified_modules as Array<Record<string, unknown>>) ?? []
  const delMods = (result.deleted_modules as Array<Record<string, unknown>>) ?? []
  const unchanged = (result.unchanged_modules as Array<Record<string, unknown>>) ?? []

  const changeColor = (change: string) => {
    switch (change) {
      case 'new': return 'text-green-600'
      case 'modified': return 'text-amber-600'
      case 'deleted': return 'text-red-600'
      default: return 'text-muted-foreground'
    }
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-5 gap-3 text-center">
        {[
          { label: '新增模块', count: newMods.length, color: 'text-green-600' },
          { label: '修改模块', count: modMods.length, color: 'text-amber-600' },
          { label: '删除模块', count: delMods.length, color: 'text-red-600' },
          { label: '不变模块', count: unchanged.length, color: 'text-muted-foreground' },
          { label: '置信度', count: `${Math.round((result.diff_confidence as number ?? 0) * 100)}%`, color: 'text-blue-600' },
        ].map((item) => (
          <div key={item.label} className="p-3 bg-muted/50 rounded-lg">
            <div className={cn('text-xl font-bold', item.color)}>{item.count}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Warnings */}
      {summary.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-xs font-medium text-amber-800 mb-1">注意事项</p>
          <ul className="list-disc list-inside text-xs text-amber-700 space-y-0.5">
            {summary.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Changed modules detail */}
      {[...newMods, ...modMods, ...delMods].length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">变更详情</p>
          <div className="max-h-[400px] overflow-auto space-y-1">
            {[...newMods, ...modMods, ...delMods].map((mod: Record<string, unknown>, i) => {
              const change = (mod.change ?? mod.__change__ ?? 'modified') as string
              const name = (mod.module_name ?? mod.name ?? `模块 ${i + 1}`) as string
              const pages = mod.new_pages
                ? `+${(mod.new_pages as Array<unknown>)?.length ?? 0} 页面`
                : ''
              return (
                <div
                  key={i}
                  className="flex items-center justify-between px-3 py-2 bg-muted/30 rounded text-sm"
                >
                  <span className={cn('font-medium', changeColor(change))}>
                    {change === 'new' ? '+ ' : change === 'deleted' ? '− ' : '~ '}
                    {name}
                  </span>
                  {pages && (
                    <span className="text-xs text-muted-foreground">{pages}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
