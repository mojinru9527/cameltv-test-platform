import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { useAuthStore } from '@/stores/auth'
import Placeholder from '@/pages/Placeholder'
import { cn } from '@/lib/utils'
import { Play, Loader2, RefreshCw, XCircle, AlertCircle, Eye } from '@/lib/icons'
import TeamProgress from './team-progress'
import {
  createDshTask,
  fetchDshTasks,
  fetchDshTask,
  fetchDshHealth,
  fetchDshModelPool,
  cancelDshTask,
  type DshTask,
  type DshHealth,
  type DshModelPool,
} from '@/api/dshTasks'
import { fetchAiResolve, fetchAiProviders, type AiResolveResult, type AiProviderItem } from '@/api/aiConfig'
import { SCENES, sceneLabel, type SceneDef } from './scenes'
import SceneWizard from './components/SceneWizard'

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'bg-muted text-muted-foreground' },
  running: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  success: { label: '成功', color: 'bg-status-success-muted text-status-success' },
  failed: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
  cancelled: { label: '已取消', color: 'bg-muted text-muted-foreground' },
}

// Batch 191：详情进度轮询粒度（与后端 DSH_TEAM_POLL_SECONDS=3 对齐）
const DETAIL_POLL_MS = 3000

export default function DshTasksPage() {
  useDocumentTitle('DSH 任务')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canView = hasPerm('agent:view') || hasPerm('agent:list')
  const canRun = hasPerm('agent:run')

  const [tasks, setTasks] = useState<DshTask[]>([])
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<DshHealth | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [taskText, setTaskText] = useState('')
  const [creating, setCreating] = useState(false)
  const [selected, setSelected] = useState<DshTask | null>(null)
  const [detail, setDetail] = useState<DshTask | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  // Batch 191：任务模式（single/team）+ 批次模式（full/light）
  const [taskMode, setTaskMode] = useState<'single' | 'team'>('single')
  const [batchMode, setBatchMode] = useState<'full' | 'light'>('full')
  // DSH 测试 Agent 框架：团队视角（dev/tester）+ 模型选择（模型池）
  const [teamKind, setTeamKind] = useState<'dev' | 'tester'>('dev')
  const [modelPool, setModelPool] = useState<DshModelPool | null>(null)
  const [selectedModel, setSelectedModel] = useState('')
  // Batch A：项目 AI 配置状态（未配置则引导去 AI 配置页）
  const [aiResolve, setAiResolve] = useState<AiResolveResult | null>(null)
  // B1：AI 提供方池（场景向导配置项）+ 向导选中场景
  const [providers, setProviders] = useState<AiProviderItem[]>([])
  const [wizardScene, setWizardScene] = useState<SceneDef | null>(null)

  const load = useCallback((signal?: AbortSignal) => {
    setLoading(true)
    fetchDshTasks({ page_size: 50 }, signal)
      .then((res) => { if (!signal?.aborted) setTasks(res.items) })
      .catch(() => { if (!signal?.aborted) toast.error('加载 DSH 任务失败') })
      .finally(() => { if (!signal?.aborted) setLoading(false) })
  }, [])

  const loadHealth = useCallback((signal?: AbortSignal) => {
    fetchDshHealth(signal)
      .then((h) => { if (!signal?.aborted) setHealth(h) })
      .catch(() => undefined)
  }, [])

  const loadModelPool = useCallback((signal?: AbortSignal) => {
    fetchDshModelPool(signal)
      .then((pool) => { if (!signal?.aborted) setModelPool(pool) })
      .catch(() => undefined)
  }, [])

  const loadAiResolve = useCallback((signal?: AbortSignal) => {
    fetchAiResolve(signal)
      .then((res) => { if (!signal?.aborted) setAiResolve(res) })
      .catch(() => undefined)
  }, [])

  // B1：场景向导需要 AI 提供方池（静默失败，空则向导内提示去配置）
  const loadProviders = useCallback((signal?: AbortSignal) => {
    fetchAiProviders(signal)
      .then((res) => { if (!signal?.aborted) setProviders(res) })
      .catch(() => undefined)
  }, [])

  useAbortableEffect((signal) => {
    load(signal)
    loadHealth(signal)
    loadModelPool(signal)
    loadAiResolve(signal)
    loadProviders(signal)
  }, [load, loadHealth, loadModelPool, loadAiResolve, loadProviders])

  useAbortableEffect((signal) => {
    if (!selected?.id) return
    setDetailLoading(true)
    fetchDshTask(selected.id, signal)
      .then((t) => { if (!signal.aborted) setDetail(t) })
      .catch(() => { if (!signal.aborted) toast.error('加载详情失败') })
      .finally(() => { if (!signal.aborted) setDetailLoading(false) })
  }, [selected?.id])

  const hasRunning = tasks.some((t) => t.status === 'running')
  useEffect(() => {
    if (!hasRunning) return
    // Batch 178（FIX-173-P2-12）：指数退避轮询（1s→2s→4s→8s→10s 封顶），
    // 避免长任务期间固定 3s 空转请求。
    let delay = 1000
    let timer: ReturnType<typeof setTimeout> | null = null
    const schedule = () => {
      timer = setTimeout(async () => {
        await load()
        delay = Math.min(delay * 2, 10_000)
        schedule()
      }, delay)
    }
    schedule()
    return () => { if (timer) clearTimeout(timer) }
  }, [hasRunning, load])

  // Batch 191：running 团队详情按 DSH_TEAM_POLL_SECONDS 粒度轮询刷新
  // （cleanup 必须 clearInterval + AbortController.abort；非 running 不轮询）
  const detailId = detail?.id
  const detailMode = detail?.mode
  const detailStatus = detail?.status
  useEffect(() => {
    if (!detailId || detailMode !== 'team' || detailStatus !== 'running') return
    const controller = new AbortController()
    const timer = setInterval(async () => {
      try {
        const t = await fetchDshTask(detailId, controller.signal)
        if (!controller.signal.aborted) setDetail(t)
      } catch (e: any) {
        if (e?.name !== 'AbortError') toast.error('刷新团队进度失败')
      }
    }, DETAIL_POLL_MS)
    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [detailId, detailMode, detailStatus])

  const handleCreate = async () => {
    if (!taskText.trim()) return
    setCreating(true)
    try {
      const params: Record<string, any> = {}
      if (selectedModel) params.model = selectedModel
      if (taskMode === 'team') {
        params.batch_mode = batchMode
        params.team_kind = teamKind
        await createDshTask(taskText.trim(), params, 'team')
      } else {
        await createDshTask(taskText.trim(), params)
      }
      toast.success('DSH 任务已提交')
      setCreateOpen(false)
      setTaskText('')
      load()
    } catch (e: any) {
      toast.error(e?.message || '提交失败')
    } finally {
      setCreating(false)
    }
  }

  const handleCancel = async (id: number) => {
    try {
      await cancelDshTask(id)
      toast.success('任务已取消')
      load()
    } catch (e: any) {
      toast.error(e?.message || '取消失败')
    }
  }

  if (!canView) {
    return <Placeholder title="需要 agent:view 权限" />
  }

  const unavailable = Boolean(health && !health.available)
  const sceneDisabled = !canRun || unavailable || Boolean(aiResolve && !aiResolve.configured)

  const handleSceneClick = (scene: SceneDef) => {
    if (sceneDisabled) return
    if (scene.id === 'general') {
      setCreateOpen(true)
      return
    }
    setWizardScene(scene)
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="DSH 任务"
        description="提交自然语言任务，由 DeepSeek Harness 智能体真实执行并返回结果与日志。"
      >
        {unavailable ? (
          <div className="flex items-center gap-2 text-xs text-status-warning bg-status-warning-muted border border-status-warning-border rounded-md px-3 py-1.5">
            <AlertCircle className="size-4" />
            {health?.reason || 'DSH 服务未启用'}
          </div>
        ) : (
          <Badge className="bg-status-success-muted text-status-success">DSH 可用</Badge>
        )}
        {aiResolve && !aiResolve.configured ? (
          <div className="flex items-center gap-2 text-xs text-status-warning bg-status-warning-muted border border-status-warning-border rounded-md px-3 py-1.5">
            <AlertCircle className="size-4" />
            当前项目未配置 AI 提供方，
            <Link to="/ai-config" className="underline">去配置</Link>
          </div>
        ) : aiResolve?.configured && aiResolve.provider ? (
          <Badge className="bg-status-success-muted text-status-success">
            AI: {aiResolve.provider.name} / {aiResolve.provider.model}
          </Badge>
        ) : null}
        <Button
          onClick={() => setCreateOpen(true)}
          disabled={!canRun || unavailable || Boolean(aiResolve && !aiResolve.configured)}
          title={aiResolve && !aiResolve.configured ? '当前项目未配置 AI 提供方，请先到 AI 配置页设置' : undefined}
        >
          <Play className="size-4 mr-1" />
          新建任务
        </Button>
        <Button variant="secondary" onClick={() => load()} disabled={loading}>
          <RefreshCw className={`size-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </PageHeader>

      {/* B1：场景卡片区（5 场景，点击打开对应向导；general 复用原新建对话框） */}
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {SCENES.map((scene) => {
              const Icon = scene.icon
              const disabled = sceneDisabled
              return (
                <button
                  key={scene.id}
                  type="button"
                  onClick={() => handleSceneClick(scene)}
                  disabled={disabled}
                  title={disabled ? (aiResolve && !aiResolve.configured ? '当前项目未配置 AI 提供方，请先到 AI 配置页设置' : 'DSH 服务不可用或无权限') : undefined}
                  className={cn(
                    'flex flex-col items-start gap-2 rounded-lg border p-3 text-left transition-colors',
                    disabled
                      ? 'cursor-not-allowed opacity-50'
                      : 'hover:border-ring hover:bg-muted/50',
                  )}
                >
                  <Icon className="size-5 text-muted-foreground" />
                  <div>
                    <div className="text-sm font-medium">{scene.label}</div>
                    <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{scene.description}</div>
                  </div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">ID</TableHead>
                <TableHead>任务</TableHead>
                <TableHead className="w-16">场景</TableHead>
                <TableHead className="w-20">状态</TableHead>
                <TableHead className="w-28">创建时间</TableHead>
                <TableHead className="w-24">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-10" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                  </TableRow>
                ))
              ) : tasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-10">
                    暂无 DSH 任务。点击「新建任务」提交第一个任务。
                  </TableCell>
                </TableRow>
              ) : (
                tasks.map((t) => {
                  const status = STATUS_BADGE[t.status] ?? { label: t.status, color: '' }
                  return (
                    <TableRow key={t.id} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelected(t)}>
                      <TableCell className="text-xs text-muted-foreground">#{t.id}</TableCell>
                      <TableCell className="text-sm truncate max-w-[26rem]" title={t.task}>
                        {t.task || '-'}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          const label = sceneLabel(t.scene)
                          if (label !== t.scene) {
                            return <Badge variant="outline">{label}</Badge>
                          }
                          return t.mode === 'team' ? (
                            <Badge className="bg-status-info-muted text-status-info">团队</Badge>
                          ) : (
                            <Badge variant="outline">标准</Badge>
                          )
                        })()}
                      </TableCell>
                      <TableCell>
                        <Badge className={status.color}>
                          {status.label}
                          {t.status === 'running' && <Loader2 className="size-3 animate-spin ml-1" />}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {t.created_at?.slice(0, 19)?.replace('T', ' ') || '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="sm" className="h-8 px-2" onClick={() => setSelected(t)}>
                            <Eye className="size-4" />
                          </Button>
                          {canRun && t.status === 'pending' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-status-danger hover:text-status-danger hover:bg-status-danger-muted"
                              onClick={() => handleCancel(t.id)}
                            >
                              <XCircle className="size-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Sheet open={!!selected} onOpenChange={(open) => { if (!open) { setSelected(null); setDetail(null) } }}>
        <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>DSH 任务详情</SheetTitle>
          </SheetHeader>
          {detailLoading ? (
            <div className="space-y-3 mt-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : detail ? (
            <div className="mt-6 space-y-4 text-sm">
              <div className="flex items-center gap-2">
                <Badge className={STATUS_BADGE[detail.status]?.color}>
                  {STATUS_BADGE[detail.status]?.label}
                </Badge>
                {detail.mode === 'team' && <Badge className="bg-status-info-muted text-status-info">团队</Badge>}
                <span className="text-xs text-muted-foreground">#{detail.id}</span>
              </div>
              {detail.error && (
                <div className="rounded-md bg-status-danger-muted border border-status-danger-border p-3">
                  <p className="text-status-danger text-xs font-mono whitespace-pre-wrap">{detail.error}</p>
                </div>
              )}
              <div>
                <h4 className="font-medium mb-1">任务</h4>
                <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap">{detail.task}</pre>
              </div>
              {sceneLabel(detail.scene) !== detail.scene && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>场景: {sceneLabel(detail.scene)}</span>
                </div>
              )}
              {/* Batch 191：团队进度树（mode=team 且快照非空） */}
              {detail.mode === 'team' && Object.keys(detail.team_json || {}).length > 0 ? (
                <div>
                  <h4 className="font-medium mb-1">团队进度</h4>
                  <TeamProgress teamJson={detail.team_json} status={detail.status} outputText={detail.output_text} />
                </div>
              ) : detail.mode === 'team' && detail.status === 'running' ? (
                <div className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
                  团队进度尚未产生，等待船长建队…
                </div>
              ) : null}
              {detail.output_text && detail.mode !== 'team' && (
                <div>
                  <h4 className="font-medium mb-1">执行输出</h4>
                  <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-96 overflow-y-auto">
                    {detail.output_text}
                  </pre>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div>创建: {detail.created_at?.slice(0, 19)?.replace('T', ' ') || '-'}</div>
                <div>开始: {detail.started_at?.slice(0, 19)?.replace('T', ' ') || '-'}</div>
                <div>完成: {detail.finished_at?.slice(0, 19)?.replace('T', ' ') || '-'}</div>
                {detail.session_dir && <div className="col-span-2 truncate" title={detail.session_dir}>会话: {detail.session_dir}</div>}
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建 DSH 任务</DialogTitle>
            <DialogDescription>
              输入自然语言任务描述，DeepSeek Harness 智能体将在受控工作区执行并返回结果。
              团队模式将创建 DSH 船长会话，自组织多成员团队执行（可选开发批次或测试视角）。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <Label htmlFor="dsh-task-text">任务描述</Label>
            <Textarea
              id="dsh-task-text"
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              placeholder="例如：检查 test-platform-v2 后端结构并总结；或：跑一遍接口回归并输出结果"
              rows={5}
            />
            {/* Batch 191：任务模式选择（标准/团队） */}
            <div>
              <Label htmlFor="dsh-task-mode">任务模式</Label>
              <Select value={taskMode} onValueChange={(v) => setTaskMode(v as 'single' | 'team')}>
                <SelectTrigger id="dsh-task-mode" aria-label="任务模式" className="w-full mt-1">
                  <SelectValue placeholder="选择任务模式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">标准模式（single）</SelectItem>
                  <SelectItem value="team">团队模式（team）</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* Batch 191：团队模式批次下拉（仅团队模式显示） */}
            {taskMode === 'team' && (
              <div>
                <Label htmlFor="dsh-task-batch-mode">批次模式</Label>
                <Select value={batchMode} onValueChange={(v) => setBatchMode(v as 'full' | 'light')}>
                  <SelectTrigger id="dsh-task-batch-mode" aria-label="批次模式" className="w-full mt-1">
                    <SelectValue placeholder="选择批次模式" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full">完整批次（full）</SelectItem>
                    <SelectItem value="light">轻量批次（light）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            {/* DSH 测试 Agent 框架：团队视角（dev 开发批次 / tester 测试视角） */}
            {taskMode === 'team' && (
              <div>
                <Label htmlFor="dsh-task-team-kind">团队视角</Label>
                <Select value={teamKind} onValueChange={(v) => setTeamKind(v as 'dev' | 'tester')}>
                  <SelectTrigger id="dsh-task-team-kind" aria-label="团队视角" className="w-full mt-1">
                    <SelectValue placeholder="选择团队视角" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dev">开发批次（PRD→QA）</SelectItem>
                    <SelectItem value="tester">测试视角（分析→用例→执行→审查）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            {/* DSH 测试 Agent 框架（阶段 3）：模型选择（模型池） */}
            {modelPool && modelPool.pool_configured && (
              <div>
                <Label htmlFor="dsh-task-model">模型</Label>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger id="dsh-task-model" aria-label="模型" className="w-full mt-1">
                    <SelectValue placeholder={modelPool.default_model || '默认模型'} />
                  </SelectTrigger>
                  <SelectContent>
                    {modelPool.models.map((m) => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">不选择则使用平台默认模型</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setCreateOpen(false)} disabled={creating}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={creating || !taskText.trim()}>
              {creating && <Loader2 className="size-4 animate-spin mr-1" />}
              提交
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {wizardScene && wizardScene.id !== 'general' && (
        <SceneWizard
          open={Boolean(wizardScene)}
          onOpenChange={(o) => { if (!o) setWizardScene(null) }}
          scene={wizardScene}
          providers={providers}
          onSubmitted={load}
        />
      )}
    </div>
  )
}
