import { Badge, Button, Input, PageShell, type BadgeTone } from '@/ui'
/**
 * Environment & Variable management page.
 * E1: Project-level environments (dev/test/staging/prod) + variables with optional encryption.
 *
 * P1-8: Migrated to useApi + AsyncState for loading/error/empty handling.
 */
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  Server, Plus, Edit, Trash2, Eye, EyeOff, Globe, Copy,
} from '@/lib/icons'
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { useAuthStore } from '@/stores/auth'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import type { Environment, EnvironmentVariable } from '@/types'
import {
  fetchEnvironments, createEnvironment, updateEnvironment, deleteEnvironment,
  fetchVariables, createVariable, updateVariable, deleteVariable,
} from '@/api/environment'
import { AsyncState } from '@/components/state'
import EmptyState from '@/components/EmptyState'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConfirmActionDialog from '@/components/ConfirmActionDialog'

const ENV_TYPE_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  dev: { label: '开发', tone: 'info' },
  test: { label: '测试', tone: 'neutral' },
  staging: { label: '预发布', tone: 'warning' },
  prod: { label: '生产', tone: 'danger' },
}

export default function EnvironmentPage() {
  useDocumentTitle('目标环境')
  // ── Environments (useApi — P1-8) ──
  const { data: envs, isLoading, isError, error, refetch } = useApi<Environment[]>(
    () => fetchEnvironments(),
    [],
  )

  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null)
  const [variables, setVariables] = useState<EnvironmentVariable[]>([])
  const [varsLoading, setVarsLoading] = useState(false)
  const canManage = useAuthStore((state) => state.hasPerm)('project:manage')

  // Dialogs
  const [envDialog, setEnvDialog] = useState(false)
  const [editEnv, setEditEnv] = useState<Environment | null>(null)
  const [varDialog, setVarDialog] = useState(false)
  const [editVar, setEditVar] = useState<EnvironmentVariable | null>(null)

  // Form state
  const [envForm, setEnvForm] = useState({ name: '', env_type: 'test' as string, base_url: '', description: '' })
  const [varForm, setVarForm] = useState({ key: '', value: '', encrypted: false, description: '' })

  // Confirmation dialogs
  const [deleteEnvTarget, setDeleteEnvTarget] = useState<Environment | null>(null)
  const [deleteVarTarget, setDeleteVarTarget] = useState<EnvironmentVariable | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [showProdTypeChangeDialog, setShowProdTypeChangeDialog] = useState(false)

  function isProductionEnv(env: Environment): boolean {
    return env.is_production === true || env.env_type === 'prod'
  }

  // ── Auto-select first env when data loads ──
  useEffect(() => {
    if (envs && envs.length > 0 && !selectedEnv) {
      setSelectedEnv(envs[0])
    }
  }, [envs, selectedEnv])

  // ── Variables loading (on-demand per selected env) ──
  const loadVars = useCallback(async (envId: number, isCancelled?: () => boolean) => {
    setVarsLoading(true)
    try {
      const data = await fetchVariables(envId)
      // Batch 176（FIX-173-P1-02）：快速切换环境时旧响应不得覆盖新环境变量（竞态守卫）
      if (!isCancelled?.()) setVariables(data)
    } catch { /* handled by interceptor */ }
    finally { if (!isCancelled?.()) setVarsLoading(false) }
  }, [])

  useEffect(() => {
    if (!selectedEnv) return
    let cancelled = false
    void loadVars(selectedEnv.id, () => cancelled)
    return () => { cancelled = true }
  }, [selectedEnv, loadVars])

  // ── Environment handlers ──

  const openEnvCreate = () => {
    setEditEnv(null)
    setEnvForm({ name: '', env_type: 'test', base_url: '', description: '' })
    setEnvDialog(true)
  }

  const openEnvEdit = (env: Environment) => {
    setEditEnv(env)
    setEnvForm({ name: env.name, env_type: env.env_type, base_url: env.base_url, description: env.description })
    setEnvDialog(true)
  }

  const doEnvSave = async () => {
    if (!envForm.name.trim()) { toast.error('请输入环境名称'); return }
    try {
      if (editEnv) {
        await updateEnvironment(editEnv.id, envForm)
        if (selectedEnv?.id === editEnv.id) {
          // Refresh selected env details
          const updated = envs?.find((e) => e.id === editEnv.id)
          if (updated) {
            setSelectedEnv({ ...updated, ...envForm })
          }
        }
        toast.success('环境已更新')
      } else {
        const created = await createEnvironment(envForm)
        setSelectedEnv(created)
        toast.success('环境已创建')
      }
      setEnvDialog(false)
      refetch()
    } catch { /* handled by interceptor */ }
  }

  const handleEnvSave = async () => {
    if (!envForm.name.trim()) { toast.error('请输入环境名称'); return }
    // When editing a production env and changing type away from prod, confirm first
    if (editEnv && isProductionEnv(editEnv) && envForm.env_type !== 'prod') {
      setShowProdTypeChangeDialog(true)
      return
    }
    await doEnvSave()
  }

  const handleEnvDelete = async (env: Environment) => {
    setDeleteEnvTarget(env)
  }

  const confirmDeleteEnv = async () => {
    if (!deleteEnvTarget) return
    setDeleting(true)
    try {
      await deleteEnvironment(deleteEnvTarget.id)
      if (selectedEnv?.id === deleteEnvTarget.id) setSelectedEnv(null)
      toast.success('环境已删除')
      setDeleteEnvTarget(null)
      refetch()
    } catch { /* handled by interceptor */ }
    finally { setDeleting(false) }
  }

  // ── Variable handlers ──

  const openVarCreate = () => {
    if (!selectedEnv) { toast.error('请先选择一个环境'); return }
    setEditVar(null)
    setVarForm({ key: '', value: '', encrypted: false, description: '' })
    setVarDialog(true)
  }

  const openVarEdit = (v: EnvironmentVariable) => {
    setEditVar(v)
    setVarForm({ key: v.key, value: v.encrypted ? '' : v.value, encrypted: v.encrypted, description: v.description })
    setVarDialog(true)
  }

  const handleVarSave = async () => {
    if (!selectedEnv) return
    if (!varForm.key.trim()) { toast.error('请输入变量名'); return }
    try {
      if (editVar) {
        const body: Record<string, any> = { key: varForm.key, encrypted: varForm.encrypted, description: varForm.description }
        if (varForm.value) body.value = varForm.value
        await updateVariable(selectedEnv.id, editVar.id, body)
        toast.success('变量已更新')
      } else {
        await createVariable(selectedEnv.id, varForm)
        toast.success('变量已创建')
      }
      setVarDialog(false)
      if (selectedEnv) loadVars(selectedEnv.id)
    } catch { /* handled by interceptor */ }
  }

  const handleVarDelete = async (v: EnvironmentVariable) => {
    setDeleteVarTarget(v)
  }

  const confirmDeleteVar = async () => {
    if (!selectedEnv || !deleteVarTarget) return
    setDeleting(true)
    try {
      await deleteVariable(selectedEnv.id, deleteVarTarget.id)
      toast.success('变量已删除')
      setDeleteVarTarget(null)
      if (selectedEnv) loadVars(selectedEnv.id)
    } catch { /* handled by interceptor */ }
    finally { setDeleting(false) }
  }

  // ── Render ──

  return (
    <PageShell
      title="环境与变量管理"
      description="项目级测试环境配置与加密变量管理，支持环境切换与变量引用。"
      actions={canManage ? (
        <Button className="min-h-11" onClick={openEnvCreate}>
          <Plus className="size-4" data-icon="inline-start" />
          新建环境
        </Button>
      ) : undefined}
      glass
    >
      <div className="space-y-4">
      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={envs}
        onRetry={refetch}
        emptyTitle="暂无环境"
        emptyDescription={'点击"新建环境"创建第一个测试环境'}
        emptyAction={canManage ? { label: '新建环境', onClick: openEnvCreate } : undefined}
      >
        {(envList) => (
          <>
            {/* Environment tabs */}
            <div className="flex flex-wrap gap-2">
              {envList.map((env) => (
                <Button
                  key={env.id}
                  variant={selectedEnv?.id === env.id ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setSelectedEnv(env)}
                >
                  <Server className="size-3.5" data-icon="inline-start" />
                  {env.name}
                  <Badge tone={ENV_TYPE_MAP[env.env_type]?.tone ?? 'neutral'} className="ml-2 text-xs px-1.5 py-0">
                    {ENV_TYPE_MAP[env.env_type]?.label ?? env.env_type}
                  </Badge>
                </Button>
              ))}
            </div>

            {/* Selected environment detail */}
            {selectedEnv && (
              <Card className="ui-surface">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Globe className="size-5 text-muted-foreground" />
                      <div>
                        <CardTitle className="text-lg">{selectedEnv.name}</CardTitle>
                        <CardDescription>{selectedEnv.description || selectedEnv.base_url || '未设置描述'}</CardDescription>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {canManage && (
                        <Button variant="ghost" size="icon" onClick={() => openEnvEdit(selectedEnv)} aria-label="编辑环境" title="编辑环境">
                          <Edit className="size-4" />
                        </Button>
                      )}
                      {canManage && (
                        <Button variant="ghost" size="icon" onClick={() => handleEnvDelete(selectedEnv)} aria-label="删除环境" title="删除环境">
                          <Trash2 className="size-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold">变量列表</h3>
                    {canManage && (
                      <Button variant="secondary" size="sm" className="min-h-11" onClick={openVarCreate}>
                        <Plus className="size-3.5" data-icon="inline-start" />添加变量
                      </Button>
                    )}
                  </div>

                  {varsLoading ? (
                    <p className="text-sm text-muted-foreground py-8 text-center">加载变量中…</p>
                  ) : variables.length === 0 ? (
                    <EmptyState
                      title="暂无变量"
                      description={'点击"添加变量"开始配置'}
                      className="py-8"
                    />
                  ) : (
                    <Table className="ui-table">
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[180px]">变量名</TableHead>
                          <TableHead>值</TableHead>
                          <TableHead className="w-[80px]">加密</TableHead>
                          <TableHead className="w-[200px]">描述</TableHead>
                          <TableHead className="w-[100px]">操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {variables.map((v) => (
                          <TableRow key={v.id}>
                            <TableCell className="font-mono text-sm">{v.key}</TableCell>
                            <TableCell className="font-mono text-sm text-muted-foreground max-w-[200px] truncate" title={v.encrypted ? undefined : v.value}>
                              {v.encrypted ? '••••••••' : v.value}
                            </TableCell>                            <TableCell>
                              {v.encrypted ? (
                                <Badge tone="warning" className="text-xs">加密</Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">明文</span>
                              )}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">{v.description}</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                {!v.encrypted && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    aria-label={`复制变量 ${v.key}`}
                                    title="复制值"
                                    onClick={() => {
                                      navigator.clipboard?.writeText(v.value || '').then(
                                        () => toast.success(`已复制 ${v.key}`),
                                        () => toast.error('复制失败'),
                                      ).catch(() => toast.error('复制失败'))
                                    }}
                                  >
                                    <Copy className="size-3.5" />
                                  </Button>
                                )}
                                {canManage && (
                                  <Button variant="ghost" size="icon" onClick={() => openVarEdit(v)} aria-label={`编辑变量 ${v.key}`} title="编辑">
                                    <Edit className="size-3.5" />
                                  </Button>
                                )}
                                {canManage && (
                                  <Button variant="ghost" size="icon" onClick={() => handleVarDelete(v)} aria-label={`删除变量 ${v.key}`} title="删除">
                                    <Trash2 className="size-3.5 text-destructive" />
                                  </Button>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            )}
          </>
        )}
      </AsyncState>

      {/* Environment dialog */}
      <Dialog open={envDialog} onOpenChange={setEnvDialog}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>{editEnv ? '编辑环境' : '新建环境'}</DialogTitle>
            <DialogDescription>配置项目级测试环境信息</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium" htmlFor="env-name">环境名称 *</label>
              <Input id="env-name" value={envForm.name} onChange={(e) => setEnvForm((f) => ({ ...f, name: e.target.value }))} placeholder="如：开发环境" />
            </div>
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium">环境类型</label>
              <Select value={envForm.env_type} onValueChange={(v) => setEnvForm((f) => ({ ...f, env_type: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="dev">开发 (dev)</SelectItem>
                  <SelectItem value="test">测试 (test)</SelectItem>
                  <SelectItem value="staging">预发布 (staging)</SelectItem>
                  <SelectItem value="prod">生产 (prod)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium" htmlFor="env-url">Base URL</label>
              <Input id="env-url" value={envForm.base_url} onChange={(e) => setEnvForm((f) => ({ ...f, base_url: e.target.value }))} placeholder="https://api.example.com" />
            </div>
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium" htmlFor="env-desc">描述</label>
              <Textarea id="env-desc" value={envForm.description} onChange={(e) => setEnvForm((f) => ({ ...f, description: e.target.value }))} placeholder="环境用途说明" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setEnvDialog(false)}>取消</Button>
            <Button onClick={handleEnvSave}>{editEnv ? '保存' : '创建'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Variable dialog */}
      <Dialog open={varDialog} onOpenChange={setVarDialog}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>{editVar ? '编辑变量' : '添加变量'}</DialogTitle>
            <DialogDescription>变量可在 API 测试中通过 $&#123;KEY&#125; 引用</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium" htmlFor="var-key">变量名 *</label>
              <Input id="var-key" value={varForm.key} onChange={(e) => setVarForm((f) => ({ ...f, key: e.target.value }))} placeholder="如：BASE_URL" />
            </div>
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium" htmlFor="var-value">值</label>
              <div className="relative">
                <Input
                  id="var-value"
                  type={varForm.encrypted ? 'password' : 'text'}
                  value={varForm.value}
                  onChange={(e) => setVarForm((f) => ({ ...f, value: e.target.value }))}
                  placeholder={editVar?.encrypted ? '留空则不修改原值' : '变量值'}
                />
                <Button
                  variant="ghost" size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 size-7"
                  onClick={() => setVarForm((f) => ({ ...f, encrypted: !f.encrypted }))}
                  aria-label={varForm.encrypted ? '以明文显示变量值' : '隐藏变量值'}
                >
                  {varForm.encrypted ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                </Button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Switch id="var-enc" checked={varForm.encrypted} onCheckedChange={(v) => setVarForm((f) => ({ ...f, encrypted: v }))} />
              <label htmlFor="var-enc" className="text-sm">加密存储（AES-128）</label>
            </div>
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium" htmlFor="var-desc">描述</label>
              <Input id="var-desc" value={varForm.description} onChange={(e) => setVarForm((f) => ({ ...f, description: e.target.value }))} placeholder="变量用途说明" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setVarDialog(false)}>取消</Button>
            <Button onClick={handleVarSave}>{editVar ? '保存' : '添加'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmActionDialog
        open={deleteEnvTarget !== null}
        onOpenChange={(open) => { if (!open && !deleting) setDeleteEnvTarget(null) }}
        title={deleteEnvTarget && isProductionEnv(deleteEnvTarget) ? '删除生产环境确认' : '删除环境'}
        description={
          deleteEnvTarget && isProductionEnv(deleteEnvTarget)
            ? `您正在删除生产环境配置「${deleteEnvTarget.name}」，此操作可能影响线上测试，且其中的变量也将被删除。`
            : `确定删除环境「${deleteEnvTarget?.name ?? ''}」？其中的变量也将被删除。`
        }
        pending={deleting}
        onConfirm={confirmDeleteEnv}
      />

      <ConfirmActionDialog
        open={deleteVarTarget !== null}
        onOpenChange={(open) => { if (!open && !deleting) setDeleteVarTarget(null) }}
        title="删除环境变量"
        description={`确定删除变量「${deleteVarTarget?.key ?? ''}」？此操作无法撤销。`}
        pending={deleting}
        onConfirm={confirmDeleteVar}
      />

      {/* Production env type change confirmation */}
      <AlertDialog open={showProdTypeChangeDialog} onOpenChange={setShowProdTypeChangeDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>更改生产环境类型确认</AlertDialogTitle>
            <AlertDialogDescription>
              您正在将生产环境「{editEnv?.name}」的类型从"生产"修改为其他类型，这可能影响依赖于该环境的测试计划。请确认。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => { setShowProdTypeChangeDialog(false); doEnvSave() }}>确认修改</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </PageShell>
  )
}
