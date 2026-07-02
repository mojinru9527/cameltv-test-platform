/**
 * Environment & Variable management page.
 * E1: Project-level environments (dev/test/staging/prod) + variables with optional encryption.
 */
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  Server, Plus, Edit, Trash2, Eye, EyeOff, Key, Globe, FileText,
} from '@/lib/icons'
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import type { Environment, EnvironmentVariable } from '@/types'
import {
  fetchEnvironments, createEnvironment, updateEnvironment, deleteEnvironment,
  fetchVariables, createVariable, updateVariable, deleteVariable,
} from '@/api/environment'

const ENV_TYPE_MAP: Record<string, { label: string; color: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  dev: { label: '开发', color: 'secondary' },
  test: { label: '测试', color: 'outline' },
  staging: { label: '预发布', color: 'default' },
  prod: { label: '生产', color: 'destructive' },
}

export default function EnvironmentPage() {
  const [envs, setEnvs] = useState<Environment[]>([])
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null)
  const [variables, setVariables] = useState<EnvironmentVariable[]>([])
  const [loading, setLoading] = useState(false)

  // Dialogs
  const [envDialog, setEnvDialog] = useState(false)
  const [editEnv, setEditEnv] = useState<Environment | null>(null)
  const [varDialog, setVarDialog] = useState(false)
  const [editVar, setEditVar] = useState<EnvironmentVariable | null>(null)

  // Form state
  const [envForm, setEnvForm] = useState({ name: '', env_type: 'test', base_url: '', description: '' })
  const [varForm, setVarForm] = useState({ key: '', value: '', encrypted: false, description: '' })

  const loadEnvs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchEnvironments()
      setEnvs(data)
      if (data.length > 0 && !selectedEnv) setSelectedEnv(data[0])
    } catch { /* handled by interceptor */ }
    finally { setLoading(false) }
  }, [selectedEnv])

  const loadVars = useCallback(async (envId: number) => {
    try {
      const data = await fetchVariables(envId)
      setVariables(data)
    } catch { /* handled by interceptor */ }
  }, [])

  useEffect(() => { loadEnvs() }, [loadEnvs])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedEnv) loadVars(selectedEnv.id)
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

  const handleEnvSave = async () => {
    if (!envForm.name.trim()) { toast.error('请输入环境名称'); return }
    try {
      if (editEnv) {
        const updated = await updateEnvironment(editEnv.id, envForm)
        setEnvs((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
        if (selectedEnv?.id === updated.id) setSelectedEnv(updated)
        toast.success('环境已更新')
      } else {
        const created = await createEnvironment(envForm)
        setEnvs((prev) => [...prev, created])
        setSelectedEnv(created)
        toast.success('环境已创建')
      }
      setEnvDialog(false)
    } catch { /* handled by interceptor */ }
  }

  const handleEnvDelete = async (env: Environment) => {
    if (!confirm(`确定删除环境「${env.name}」？其中的变量也将被删除。`)) return
    try {
      await deleteEnvironment(env.id)
      setEnvs((prev) => prev.filter((e) => e.id !== env.id))
      if (selectedEnv?.id === env.id) setSelectedEnv(null)
      toast.success('环境已删除')
    } catch { /* handled by interceptor */ }
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
        if (varForm.value) body.value = varForm.value  // only send value if changed
        const updated = await updateVariable(selectedEnv.id, editVar.id, body)
        setVariables((prev) => prev.map((v) => (v.id === updated.id ? updated : v)))
        toast.success('变量已更新')
      } else {
        const created = await createVariable(selectedEnv.id, varForm)
        setVariables((prev) => [...prev, created])
        toast.success('变量已创建')
      }
      setVarDialog(false)
    } catch { /* handled by interceptor */ }
  }

  const handleVarDelete = async (v: EnvironmentVariable) => {
    if (!selectedEnv) return
    if (!confirm(`确定删除变量「${v.key}」？`)) return
    try {
      await deleteVariable(selectedEnv.id, v.id)
      setVariables((prev) => prev.filter((x) => x.id !== v.id))
      toast.success('变量已删除')
    } catch { /* handled by interceptor */ }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">环境与变量管理</h1>
          <p className="text-sm text-muted-foreground mt-1">项目级测试环境配置与加密变量管理</p>
        </div>
        <Button onClick={openEnvCreate}><Plus className="size-4" data-icon="inline-start" />新建环境</Button>
      </div>

      {/* Environment tabs */}
      <div className="flex flex-wrap gap-2">
        {envs.map((env) => (
          <Button
            key={env.id}
            variant={selectedEnv?.id === env.id ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedEnv(env)}
          >
            <Server className="size-3.5" data-icon="inline-start" />
            {env.name}
            <Badge variant={ENV_TYPE_MAP[env.env_type]?.color ?? 'outline'} className="ml-2 text-[10px] px-1.5 py-0">
              {ENV_TYPE_MAP[env.env_type]?.label ?? env.env_type}
            </Badge>
          </Button>
        ))}
        {envs.length === 0 && <p className="text-sm text-muted-foreground py-4">暂无环境，点击"新建环境"开始</p>}
      </div>

      {/* Selected environment detail */}
      {selectedEnv && (
        <Card>
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
                <Button variant="ghost" size="icon" onClick={() => openEnvEdit(selectedEnv)} title="编辑环境">
                  <Edit className="size-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => handleEnvDelete(selectedEnv)} title="删除环境">
                  <Trash2 className="size-4 text-destructive" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">变量列表</h3>
              <Button variant="outline" size="sm" onClick={openVarCreate}>
                <Plus className="size-3.5" data-icon="inline-start" />添加变量
              </Button>
            </div>

            {variables.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                暂无变量，点击"添加变量"开始配置
              </p>
            ) : (
              <Table>
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
                      <TableCell className="font-mono text-sm text-muted-foreground max-w-[200px] truncate">
                        {v.encrypted ? '••••••••' : v.value}
                      </TableCell>
                      <TableCell>
                        {v.encrypted ? (
                          <Badge variant="secondary" className="text-[10px]">加密</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">明文</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{v.description}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" onClick={() => openVarEdit(v)} title="编辑">
                            <Edit className="size-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleVarDelete(v)} title="删除">
                            <Trash2 className="size-3.5 text-destructive" />
                          </Button>
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
            <Button variant="outline" onClick={() => setEnvDialog(false)}>取消</Button>
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
                  title={varForm.encrypted ? '切换为明文' : '切换为加密'}
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
            <Button variant="outline" onClick={() => setVarDialog(false)}>取消</Button>
            <Button onClick={handleVarSave}>{editVar ? '保存' : '添加'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
