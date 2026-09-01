import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, AlertCircle } from '@/lib/icons'
import { createDshTask } from '@/api/dshTasks'
import DshImageAttach, { attachFiles, clipPasteImages, type AttachImage } from './DshImageAttach'
import type { AiProviderItem } from '@/api/aiConfig'
import type { SceneDef } from '../scenes'

interface SceneWizardProps {
  open: boolean
  onOpenChange: (o: boolean) => void
  scene: SceneDef
  providers: AiProviderItem[]
  initialInput?: string
  /** 深链带入需求正文的加载态（P1-5）。 */
  prefilling?: boolean
  onSubmitted: () => void
}

export default function SceneWizard({ open, onOpenChange, scene, providers, initialInput, prefilling, onSubmitted }: SceneWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [input, setInput] = useState('')
  const [images, setImages] = useState<AttachImage[]>([])
  // Step 2 配置
  const [providerId, setProviderId] = useState<string>('')
  const [model, setModel] = useState<string>('')
  const [mode, setMode] = useState<'single' | 'team'>('team')
  const [batchMode, setBatchMode] = useState<'full' | 'light'>('full')
  const [teamKind, setTeamKind] = useState<'dev' | 'tester'>('tester')
  // Step 3 提交
  const [taskText, setTaskText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // 打开/场景切换时重置（选择 provider 与默认 model；B3 深链预填 input）
  useEffect(() => {
    if (!open) return
    setStep(1)
    setInput(initialInput ?? '')
    setImages([])
    setMode('team')
    setBatchMode('full')
    setTeamKind('tester')
    setTaskText('')
    setSubmitting(false)
    const p = providers.find((x) => x.is_default) ?? providers[0] ?? null
    setProviderId(p ? String(p.id) : '')
    setModel(p ? p.default_model || (p.models?.[0] ?? '') : '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, scene.id])

  // P2-11：providers 是异步加载的。深链（?scene=...）会在 providers 到达**之前**
  // 打开向导，上面的重置 effect 只依赖 [open, scene.id]，因此 providerId 会永远停在
  // 空串——表现为「AI 提供方」显示 placeholder、「下一步」始终置灰且无任何说明，
  // 即使项目早已配置了默认提供方。这里在 providers 到达后补一次预选。
  useEffect(() => {
    if (!open || providerId || providers.length === 0) return
    const p = providers.find((x) => x.is_default) ?? providers[0]
    setProviderId(String(p.id))
    setModel(p.default_model || (p.models?.[0] ?? ''))
  }, [open, providerId, providers])

  // P1-5：需求正文是异步拉取的，`initialInput` 会在向导打开后才变化。
  // 仅在用户尚未编辑（当前值为空或等于旧的预填值）时同步，避免覆盖用户输入。
  const [lastPrefill, setLastPrefill] = useState('')
  useEffect(() => {
    if (!open) return
    const next = initialInput ?? ''
    if (!next || next === lastPrefill) return
    setInput((cur) => (cur.trim() === '' || cur === lastPrefill ? next : cur))
    setLastPrefill(next)
  }, [open, initialInput, lastPrefill])

  const currentProvider = useMemo(
    () => providers.find((p) => String(p.id) === providerId) ?? null,
    [providers, providerId],
  )

  const hasProviders = providers.length > 0
  const readyToConfigure = Boolean(input.trim())
  const configReady = hasProviders && Boolean(providerId)

  const handleNext = () => {
    if (step === 1) {
      if (!input.trim()) return
      setTaskText(scene.buildPrompt(input))
      setStep(2)
    } else if (step === 2) {
      if (!configReady) return
      setStep(3)
    }
  }

  const handleSubmit = async () => {
    const text = taskText.trim()
    if (!text) return
    if (images.some((im) => !im.file_id)) {
      toast.error('图片仍在上传中，请稍候')
      return
    }
    setSubmitting(true)
    try {
      const params: Record<string, any> = {}
      if (model) params.model = model
      if (mode === 'team') {
        params.batch_mode = batchMode
        params.team_kind = teamKind
      }
      if (images.length) params.image_files = images.map((im) => im.file_id)
      await createDshTask(text, params, mode, scene.id, { text: input })
      toast.success('DSH 任务已提交')
      onSubmitted()
      onOpenChange(false)
    } catch (e: any) {
      toast.error(e?.message || '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {(() => {
              const Icon = scene.icon
              return <Icon className="size-4" />
            })()}
            {scene.label}
          </DialogTitle>
          <DialogDescription>{scene.description}</DialogDescription>
        </DialogHeader>

        {/* 步骤指示 */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {['输入', '配置', '提交'].map((label, i) => {
            const n = (i + 1) as 1 | 2 | 3
            const active = step === n
            return (
              <span key={label} className="flex items-center gap-2">
                <Badge className={active ? 'bg-status-info-muted text-status-info' : 'bg-muted text-muted-foreground'}>
                  {n}. {label}
                </Badge>
                {i < 2 && <span className="text-muted-foreground/40">→</span>}
              </span>
            )
          })}
        </div>

        {step === 1 && (
          <div className="space-y-2 py-2">
            <Label htmlFor="scene-wizard-input">{scene.inputLabel}</Label>
            {prefilling && (
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="size-3 animate-spin" />
                正在带入需求正文…
              </p>
            )}
            <Textarea
              id="scene-wizard-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPaste={(e) => {
                const files = clipPasteImages(e)
                if (files.length) {
                  e.preventDefault()
                  attachFiles(setImages, files)
                }
              }}
              placeholder={scene.inputPlaceholder}
              rows={scene.inputRows}
            />
            <DshImageAttach images={images} setImages={setImages} />
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3 py-2">
            {!hasProviders ? (
              <div className="flex items-center gap-2 rounded-md border border-status-warning-border bg-status-warning-muted p-3 text-sm text-status-warning">
                <AlertCircle className="size-4 shrink-0" />
                <span>
                  当前项目未配置 AI 提供方，
                  <Link to="/ai-config" className="underline">去配置</Link>
                </span>
              </div>
            ) : (
              <>
                <div>
                  <Label htmlFor="scene-wizard-provider">AI 提供方</Label>
                  <Select value={providerId} onValueChange={setProviderId}>
                    <SelectTrigger id="scene-wizard-provider" aria-label="AI 提供方" className="w-full mt-1">
                      <SelectValue placeholder="选择 AI 提供方" />
                    </SelectTrigger>
                    <SelectContent>
                      {providers.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="scene-wizard-model">模型</Label>
                  <Select value={model} onValueChange={setModel}>
                    <SelectTrigger id="scene-wizard-model" aria-label="模型" className="w-full mt-1">
                      <SelectValue placeholder={currentProvider?.default_model || '默认模型'} />
                    </SelectTrigger>
                    <SelectContent>
                      {(currentProvider?.models?.length ? currentProvider.models : [currentProvider?.default_model || model].filter(Boolean)).map((m) => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="scene-wizard-mode">任务模式</Label>
                  <Select value={mode} onValueChange={(v) => setMode(v as 'single' | 'team')}>
                    <SelectTrigger id="scene-wizard-mode" aria-label="任务模式" className="w-full mt-1">
                      <SelectValue placeholder="选择任务模式" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="team">团队（测试视角）</SelectItem>
                      <SelectItem value="single">标准模式</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {mode === 'team' && (
                  <>
                    <div>
                      <Label htmlFor="scene-wizard-batch">批次模式</Label>
                      <Select value={batchMode} onValueChange={(v) => setBatchMode(v as 'full' | 'light')}>
                        <SelectTrigger id="scene-wizard-batch" aria-label="批次模式" className="w-full mt-1">
                          <SelectValue placeholder="选择批次模式" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="full">完整批次（full）</SelectItem>
                          <SelectItem value="light">轻量批次（light）</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="scene-wizard-team-kind">团队视角</Label>
                      <Select value={teamKind} onValueChange={(v) => setTeamKind(v as 'dev' | 'tester')}>
                        <SelectTrigger id="scene-wizard-team-kind" aria-label="团队视角" className="w-full mt-1">
                          <SelectValue placeholder="选择团队视角" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="tester">测试视角（分析→用例→执行→审查）</SelectItem>
                          <SelectItem value="dev">开发批次（PRD→QA）</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-2 py-2">
            <Label htmlFor="scene-wizard-task-text">任务描述（可编辑）</Label>
            <Textarea
              id="scene-wizard-task-text"
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              rows={10}
            />
          </div>
        )}

        <DialogFooter>
          {/* P2-11：置灰必须给出原因，否则用户只看到点不动的「下一步」。
              无 providers 时步骤内已有醒目的「去配置」提示，此处不重复。 */}
          {step === 1 && !readyToConfigure && (
            <span className="mr-auto text-xs text-muted-foreground">
              请先填写{scene.inputLabel}
            </span>
          )}
          {step === 2 && !configReady && hasProviders && (
            <span className="mr-auto text-xs text-muted-foreground">请先选择 AI 提供方</span>
          )}
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={submitting}>
            取消
          </Button>
          {step > 1 && (
            <Button variant="secondary" onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3)} disabled={submitting}>
              上一步
            </Button>
          )}
          {step < 3 && (
            <Button onClick={handleNext} disabled={step === 1 ? !readyToConfigure : !configReady}>
              下一步
            </Button>
          )}
          {step === 3 && (
            <Button onClick={handleSubmit} disabled={submitting || !taskText.trim()}>
              {submitting && <Loader2 className="size-4 animate-spin mr-1" />}
              提交
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
