import { useCallback, useState } from 'react'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { Button, Badge, Input, Label } from '@/ui'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import ConfirmActionDialog from '@/components/ConfirmActionDialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { useAuthStore } from '@/stores/auth'
import { Loader2, Plus, RefreshCw, Trash2, Pencil, Zap } from '@/lib/icons'
import {
  fetchAiProviders,
  createAiProvider,
  updateAiProvider,
  deleteAiProvider,
  testAiProviderConnection,
  fetchAiResolve,
  discoverAiModels,
  type AiProviderItem,
  type AiResolveResult,
} from '@/api/aiConfig'

const TYPE_LABELS: Record<string, string> = {
  openai_compatible: 'OpenAI 兼容',
  deepseek_official: 'DeepSeek 官方',
}

// 主流大模型官方一键模板：预置该厂商全量官方模型 + 官方 base_url + 默认模型；填入对应官方 Key 后可在
// 表单「自动发现」按厂商 /models 拉取最新全量模型清单（模板模型是稳定基线，发现结果为动态全量）。
interface OfficialTemplate {
  key: string
  name: string
  provider_type: string
  base_url: string
  models: string[]
  default_model: string
}
const OFFICIAL_TEMPLATES: OfficialTemplate[] = [
  {
    key: 'deepseek', name: 'DeepSeek 官方', provider_type: 'deepseek_official',
    base_url: 'https://api.deepseek.com',
    models: ['deepseek-v4-pro', 'deepseek-v4-flash', 'deepseek-v4-flash-preview', 'deepseek-chat', 'deepseek-reasoner'],
    default_model: 'deepseek-v4-pro',
  },
  {
    key: 'glm', name: 'GLM（智谱）', provider_type: 'openai_compatible',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4-plus', 'glm-4', 'glm-4-flash', 'glm-4-air', 'glm-4-airx', 'glm-4-0520', 'glm-4v-plus', 'glm-4v-flash'],
    default_model: 'glm-4-plus',
  },
  {
    key: 'openai', name: 'GPT（OpenAI）', provider_type: 'openai_compatible',
    base_url: 'https://api.openai.com/v1',
    models: ['gpt-5', 'gpt-5-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini', 'gpt-4.5', 'gpt-4.5-preview'],
    default_model: 'gpt-4o',
  },
  {
    key: 'qwen', name: '通义千问（Qwen）', provider_type: 'openai_compatible',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-max', 'qwen-max-latest', 'qwen-plus', 'qwen-plus-latest', 'qwen-turbo', 'qwen-turbo-latest', 'qwen-long', 'qwen3-max', 'qwen3-plus'],
    default_model: 'qwen-max',
  },
]

function dedupeModels(list: string[]): string[] {
  return Array.from(new Set(list.map((m) => m.trim()).filter(Boolean)))
}

interface FormState {
  id: number | null
  name: string
  provider_type: string
  api_base_url: string
  api_key: string
  modelsText: string
  default_model: string
  is_default: boolean
  enabled: boolean
}

const EMPTY_FORM: FormState = {
  id: null,
  name: '',
  provider_type: 'openai_compatible',
  api_base_url: '',
  api_key: '',
  modelsText: '',
  default_model: '',
  is_default: false,
  enabled: true,
}

function toForm(item: AiProviderItem): FormState {
  return {
    id: item.id,
    name: item.name,
    provider_type: item.provider_type,
    api_base_url: item.api_base_url,
    api_key: '',
    modelsText: (item.models || []).join(', '),
    default_model: item.default_model,
    is_default: item.is_default,
    enabled: item.enabled,
  }
}

export default function AiConfigPage() {
  useDocumentTitle('AI 配置')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canManage = hasPerm('ai_config:manage')

  const [providers, setProviders] = useState<AiProviderItem[]>([])
  const [resolved, setResolved] = useState<AiResolveResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [discovering, setDiscovering] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<AiProviderItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadResolved = useCallback((signal?: AbortSignal) => {
    fetchAiResolve(signal)
      .then((r) => { if (!signal?.aborted) setResolved(r) })
      .catch(() => { if (!signal?.aborted) setResolved(null) })
  }, [])

  const load = useCallback((signal?: AbortSignal) => {
    setLoading(true)
    fetchAiProviders(signal)
      .then((items) => { if (!signal?.aborted) setProviders(items) })
      .catch(() => { if (!signal?.aborted) toast.error('加载 AI 配置失败') })
      .finally(() => { if (!signal?.aborted) setLoading(false) })
    loadResolved(signal)
  }, [loadResolved])

  useAbortableEffect((signal) => {
    load(signal)
  }, [load])

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setFormOpen(true)
  }

  const openEdit = (item: AiProviderItem) => {
    setForm(toForm(item))
    setFormOpen(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error('请填写提供方名称')
      return
    }
    const models = dedupeModels(form.modelsText.split(/[,，]/))
    if (models.length === 0) {
      toast.error('至少填写一个模型')
      return
    }
    const body: Record<string, unknown> = {
      name: form.name.trim(),
      provider_type: form.provider_type,
      api_base_url: form.api_base_url.trim(),
      models,
      default_model: form.default_model.trim() || models[0],
      is_default: form.is_default,
      enabled: form.enabled,
    }
    if (form.api_key.trim()) body.api_key = form.api_key.trim()
    setSaving(true)
    try {
      if (form.id === null) {
        await createAiProvider(body)
        toast.success('AI 提供方已创建')
      } else {
        await updateAiProvider(form.id, body)
        toast.success('AI 提供方已更新')
      }
      setFormOpen(false)
      load()
    } catch (e: any) {
      toast.error(e?.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async (id: number) => {
    setTestingId(id)
    try {
      const res = await testAiProviderConnection(id)
      if (res.ok) {
        toast.success(`连通正常 (${res.latency_ms ?? '-'} ms) · ${res.model ?? ''}`)
      } else {
        // P2-7：后端已返回可执行中文提示；Key 类问题额外给出「立即更新」入口。
        const needsKey = res.kind === 'unauthorized' || res.kind === 'forbidden'
        toast.error(res.error || '连接失败', {
          duration: 10_000,
          description: res.detail && res.detail !== res.error ? res.detail : undefined,
          action: needsKey
            ? {
                label: '更新密钥',
                onClick: () => {
                  const target = providers.find((p) => p.id === id)
                  if (target) openEdit(target)
                },
              }
            : undefined,
        })
      }
      // 连通性结果会写入后端健康态，刷新生效模型卡片的状态徽标。
      loadResolved()
    } catch (e: any) {
      toast.error(e?.message || '连接失败')
    } finally {
      setTestingId(null)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteAiProvider(deleteTarget.id)
      toast.success('AI 提供方已删除')
      setDeleteTarget(null)
      load()
    } catch (e: any) {
      toast.error(e?.message || '删除失败')
    } finally {
      setDeleting(false)
    }
  }

  const handleDiscoverModels = async () => {
    if (!form.api_base_url.trim()) {
      toast.error('请先填写 API 地址')
      return
    }
    setDiscovering(true)
    try {
      const res = await discoverAiModels({
        api_base_url: form.api_base_url.trim(),
        api_key: form.api_key.trim(),
      })
      // 业务失败仍走 HTTP 200。若不早退，res.models 为 undefined 会与既有模板模型合并出
      // 非空清单，从而弹出绿色成功提示——这就是 DEF-20260905-004 的「假成功」。
      if (res.ok === false) {
        // 不给「更新密钥」action：发现发生在抽屉内部，再开一次编辑抽屉会嵌套。
        toast.error(res.error || '模型发现失败', { duration: 10_000 })
        return
      }
      // 合并厂商 /models 返回的全量模型 + 当前已填模型（去重），不丢失已知官方模型。
      const merged = dedupeModels([...dedupeModels(form.modelsText.split(/[,，]/)), ...(res?.models ?? [])])
      if (merged.length === 0) {
        toast.error('未发现可用模型')
      } else {
        setForm({
          ...form,
          modelsText: merged.join(', '),
          default_model: form.default_model.trim() || merged[0],
        })
        toast.success(`已拉取 ${res.count ?? merged.length} 个模型，合并后共 ${merged.length} 个`)
      }
    } catch (e: any) {
      toast.error(e?.message || '模型发现失败')
    } finally {
      setDiscovering(false)
    }
  }

  const handleTemplate = (tpl: OfficialTemplate) => {
    setForm({
      ...form,
      provider_type: tpl.provider_type,
      api_base_url: tpl.base_url,
      modelsText: tpl.models.join(', '),
      default_model: tpl.default_model,
    })
    if (form.id === null) setForm((f) => ({ ...f, name: tpl.name }))
    toast.success(`已填入「${tpl.name}」模板，填 API Key 后保存即可`)
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="AI 配置（AITDE 大模型）"
        description="接入 AITDE / AI 用例生成等能力需在此配置「大模型 + API Key」。此处配置的提供方为项目生效模型，AITDE 按项目解析使用；Key 加密存储、列表仅显示掩码。"
      >
        {canManage && (
          <Button onClick={openCreate}>
            <Plus className="size-4 mr-1" />
            新建提供方
          </Button>
        )}
        <Button variant="secondary" onClick={() => load()} disabled={loading}>
          <RefreshCw className={`size-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </PageHeader>

      {resolved && (
        <div className="rounded-lg border bg-card px-4 py-3 text-sm text-card-foreground">
          <div className="flex flex-wrap items-center gap-2">
            <Zap className="size-4 text-primary" />
            <span className="font-medium">AITDE 当前生效模型</span>
            {resolved.configured && resolved.provider ? (
              <span className="ml-1 flex flex-wrap items-center gap-2">
                <Badge className="bg-status-success-muted text-status-success">{resolved.provider.model}</Badge>
                <span className="text-xs text-muted-foreground">提供方：{resolved.provider.name}</span>
                {/* P0-2/P2-6：已配置 ≠ 可用。展示最近一次真实调用/连通性结果。 */}
                {resolved.health?.status === 'error' && (
                  <Badge className="bg-status-danger-muted text-status-danger">不可用</Badge>
                )}
                {resolved.health?.status === 'ok' && (
                  <Badge className="bg-status-success-muted text-status-success">连通正常</Badge>
                )}
                {(!resolved.health || resolved.health.status === 'unknown') && (
                  <Badge variant="outline">未验证</Badge>
                )}
              </span>
            ) : (
              <Badge variant="outline">未配置</Badge>
            )}
          </div>
          {!resolved.configured && (
            <p className="mt-1 text-xs text-muted-foreground">
              尚未配置生效的大模型与 Key。点击「新建提供方」填写 API 地址、模型与 API Key 并置为默认，AITDE 即可调用。
            </p>
          )}
          {resolved.configured && resolved.health?.status === 'error' && (
            <p className="mt-1.5 text-xs text-status-danger">
              {resolved.health.message}
              {resolved.health.checked_at && (
                <span className="ml-1 text-muted-foreground">（检测于 {resolved.health.checked_at}）</span>
              )}
            </p>
          )}
          {resolved.configured && (!resolved.health || resolved.health.status === 'unknown') && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              尚未验证该 Key 是否可用。点击提供方行末的「测试连通性」可立即确认，避免配置看起来正常但调用时才失败。
            </p>
          )}
        </div>
      )}

      <div className="rounded-lg border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">AITDE 使用指引</p>
        <ul className="mt-1 list-disc space-y-0.5 pl-4">
          {/* P2-8：原文案写「aitde_v3_enabled 默认关闭」，但真正卡住入口的是**前端构建变量**，
              用户照此排查无解。现改为说明开关以后端为准、前端自动跟随。 */}
          <li>
            ① AITDE 主链入口由<strong className="text-foreground">后端</strong>开关
            <code className="rounded bg-background px-1">AITDE_V3_ENABLED</code> 控制；
            前端运行时读取 <code className="rounded bg-background px-1">GET /api/v2/health</code> 自动跟随，
            改后端配置并重启即可，<strong className="text-foreground">无需重新构建前端</strong>。
          </li>
          <li>② 此处配置的「大模型 + API Key」即 AITDE / AI 用例生成按项目生效的模型；保存 Key 后平台加密存储、列表仅显示掩码。</li>
          <li>
            ③ 保存后请点「测试连通性」确认 Key 可用——
            <strong className="text-foreground">填写成功不等于调用成功</strong>，Key 过期时所有 AI 功能都会失败。
          </li>
          <li>④ 配置按项目隔离：本项目生效配置不跨项目使用（验证隔离见后端测试）。</li>
          <li>⑤ 官方一键模板已绑定官方 base_url + 默认模型，请填入对应官方 Key，避免 key 与模型错配。</li>
        </ul>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead className="w-32">类型</TableHead>
                <TableHead>API 地址</TableHead>
                <TableHead className="w-36">Key</TableHead>
                <TableHead>模型</TableHead>
                <TableHead className="w-28">默认模型</TableHead>
                <TableHead className="w-16">默认</TableHead>
                <TableHead className="w-16">启用</TableHead>
                <TableHead className="w-28">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 8 }).map((__, j) => (
                      <TableCell key={j}><Skeleton className="h-5 w-16" /></TableCell>
                    ))}
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                  </TableRow>
                ))
              ) : providers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground py-10">
                    当前项目未配置 AI 提供方。添加提供方后，平台 AI 功能（用例生成、知识中心、DSH 任务等）即可使用。
                  </TableCell>
                </TableRow>
              ) : (
                providers.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-sm font-medium">{p.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{TYPE_LABELS[p.provider_type] ?? p.provider_type}</TableCell>
                    <TableCell className="text-xs text-muted-foreground truncate max-w-[14rem]" title={p.api_base_url}>{p.api_base_url || '-'}</TableCell>
                    <TableCell className="text-xs font-mono">{p.api_key}</TableCell>
                    <TableCell className="text-xs text-muted-foreground truncate max-w-[12rem]" title={(p.models || []).join(', ')}>
                      {(p.models || []).join(', ')}
                    </TableCell>
                    <TableCell className="text-xs">{p.default_model || '-'}</TableCell>
                    <TableCell>
                      {p.is_default && <Badge className="bg-status-info-muted text-status-info">默认</Badge>}
                    </TableCell>
                    <TableCell>
                      {p.enabled ? <Badge className="bg-status-success-muted text-status-success">启用</Badge> : <Badge variant="outline">停用</Badge>}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {/* P3-13：纯图标按钮必须带 aria-label，仅有 title 对读屏与自动化都不可达。 */}
                        <Button
                          variant="ghost" size="sm" className="h-8 px-2"
                          onClick={() => handleTestConnection(p.id)} disabled={testingId === p.id}
                          title="测试连通性"
                          aria-label={`测试连通性：${p.name}`}
                        >
                          {testingId === p.id ? <Loader2 className="size-4 animate-spin" /> : <Zap className="size-4" />}
                        </Button>
                        {canManage && (
                          <>
                            <Button
                              variant="ghost" size="sm" className="h-8 px-2"
                              onClick={() => openEdit(p)}
                              title="编辑"
                              aria-label={`编辑 AI 提供方：${p.name}`}
                            >
                              <Pencil className="size-4" />
                            </Button>
                            <Button
                              variant="ghost" size="sm" className="h-8 px-2 text-status-danger hover:text-status-danger hover:bg-status-danger-muted"
                              disabled={p.is_default} title={p.is_default ? '默认提供方不可删除' : '删除'}
                              aria-label={p.is_default ? `默认提供方不可删除：${p.name}` : `删除 AI 提供方：${p.name}`}
                              onClick={() => setDeleteTarget(p)}
                            >
                              <Trash2 className="size-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{form.id === null ? '新建 AI 提供方' : '编辑 AI 提供方'}</DialogTitle>
            <DialogDescription>
              提供方配置适用于本项目所有 AI 功能；Key 加密存储，列表仅显示掩码。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <div>
              <Label>官方一键模板（预置该厂商全量官方模型 + base_url，填入对应官方 Key）</Label>
              <div className="mt-1 grid grid-cols-2 gap-2">
                {OFFICIAL_TEMPLATES.map((tpl) => (
                  <Button
                    key={tpl.key} type="button" variant="secondary" className="justify-start"
                    onClick={() => handleTemplate(tpl)}
                    title={`${tpl.base_url} · 默认 ${tpl.default_model}`}
                  >
                    {tpl.name}
                  </Button>
                ))}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                选模板后填入该厂商官方 Key，点「自动发现」可拉取该厂商当前全部官方模型。
              </p>
            </div>
            <div>
              <Label htmlFor="provider-name">名称</Label>
              <Input
                id="provider-name" className="mt-1" value={form.name} placeholder="如：DeepSeek 官方"
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="provider-type">类型</Label>
              <Select
                value={form.provider_type}
                onValueChange={(v) => setForm({ ...form, provider_type: v, api_base_url: v === 'deepseek_official' ? 'https://api.deepseek.com' : form.api_base_url })}
              >
                <SelectTrigger id="provider-type" aria-label="提供方类型" className="w-full mt-1">
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai_compatible">OpenAI 兼容</SelectItem>
                  <SelectItem value="deepseek_official">DeepSeek 官方</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="provider-base-url">API 地址</Label>
              <Input
                id="provider-base-url" className="mt-1" value={form.api_base_url} placeholder="https://api.deepseek.com"
                onChange={(e) => setForm({ ...form, api_base_url: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="provider-key">API Key</Label>
              <Input
                id="provider-key" className="mt-1" type="password" value={form.api_key}
                placeholder={form.id === null ? 'sk-...' : '留空表示不修改'}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="provider-models">模型清单（逗号分隔）</Label>
              <div className="mt-1 flex gap-2">
                <Input
                  id="provider-models" className="flex-1" value={form.modelsText}
                  placeholder="deepseek-v4-pro, deepseek-v4-flash"
                  onChange={(e) => setForm({ ...form, modelsText: e.target.value })}
                />
                <Button
                  type="button" variant="secondary" onClick={() => void handleDiscoverModels()} disabled={discovering}
                  title="根据 API 地址 + Key 自动拉取模型清单"
                >
                  {discovering ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
                  自动发现
                </Button>
              </div>
            </div>
            <div>
              <Label htmlFor="provider-default-model">默认模型</Label>
              <Input
                id="provider-default-model" className="mt-1" value={form.default_model}
                placeholder="留空使用第一个模型"
                onChange={(e) => setForm({ ...form, default_model: e.target.value })}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="provider-is-default">设为项目默认提供方</Label>
              <Switch id="provider-is-default" checked={form.is_default} onCheckedChange={(v) => setForm({ ...form, is_default: v })} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="provider-enabled">启用</Label>
              <Switch id="provider-enabled" checked={form.enabled} onCheckedChange={(v) => setForm({ ...form, enabled: v })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setFormOpen(false)} disabled={saving}>取消</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="size-4 animate-spin mr-1" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmActionDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="删除 AI 提供方"
        description={`确定删除「${deleteTarget?.name ?? ''}」吗？删除后该提供方不可再用于 AI 调用。`}
        pending={deleting}
        onConfirm={handleDelete}
      />
    </div>
  )
}
