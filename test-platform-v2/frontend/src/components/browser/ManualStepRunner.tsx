import { useState } from 'react'
import { Badge, Button, Input, Textarea } from '@/ui'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { Play, Plus, RefreshCw, Check } from '@/lib/icons'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  addManualStep,
  completeManualStep,
  createManualSession,
  fetchManualSteps,
  MANUAL_STEP_STATUS_LABELS,
  type CompleteManualStepInput,
  type ManualSession,
  type ManualStep,
} from '@/api/browserInteractions'

export interface ManualStepRunnerProps {
  scenarioId: number
  missionId: number
  scenarioVersionId: number | null
}

const STEP_STATUSES: CompleteManualStepInput['status'][] = ['PENDING', 'DONE', 'FAILED', 'BLOCKED', 'SKIPPED']

function ManualStepItem({
  step,
  onComplete,
}: {
  step: ManualStep
  onComplete: (stepId: string, payload: CompleteManualStepInput) => Promise<void>
}) {
  const [status, setStatus] = useState<CompleteManualStepInput['status']>((step.status as CompleteManualStepInput['status']) || 'DONE')
  const [note, setNote] = useState(step.tester_note ?? '')
  const [saving, setSaving] = useState(false)
  const statusMeta = MANUAL_STEP_STATUS_LABELS[step.status]

  const submit = async () => {
    setSaving(true)
    try {
      await onComplete(step.id, { status, tester_note: note || undefined })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-md border px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-muted-foreground">#{step.sequence}</span>
        <span className="font-mono text-sm">{step.step_key}</span>
        <Badge tone={statusMeta?.tone}>{statusMeta?.label ?? step.status}</Badge>
        <span className="ml-auto font-mono text-[11px] text-muted-foreground">{step.id}</span>
      </div>
      <div className="mt-2 grid gap-2 sm:grid-cols-[10rem_1fr_auto]">
        <Select value={status} onValueChange={(v) => setStatus(v as CompleteManualStepInput['status'])}>
          <SelectTrigger>
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            {STEP_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>{MANUAL_STEP_STATUS_LABELS[s]?.label ?? s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={1}
          placeholder="测试备注"
          className="font-mono text-[11px]"
        />
        <Button variant="secondary" onClick={submit} disabled={saving}>
          <Check className="size-3.5" /> {saving ? '提交中…' : '提交'}
        </Button>
      </div>
    </div>
  )
}

/**
 * Assisted-manual runner: create a manual session, append steps, and complete
 * each step with a status (PENDING/DONE/FAILED/BLOCKED/SKIPPED) + tester note.
 */
export function ManualStepRunner({ scenarioId, scenarioVersionId }: ManualStepRunnerProps) {
  const [runId, setRunId] = useState('')
  const [session, setSession] = useState<ManualSession | null>(null)
  const [steps, setSteps] = useState<ManualStep[]>([])
  const [creating, setCreating] = useState(false)
  const [adding, setAdding] = useState(false)
  const [loading, setLoading] = useState(false)

  useAbortableEffect((signal) => {
    if (!session) return
    setLoading(true)
    fetchManualSteps(scenarioId, session.id, signal)
      .then(setSteps)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载步骤失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [scenarioId, session?.id])

  const doCreate = async () => {
    const runIdNum = Number(runId)
    if (!runIdNum) {
      toast.error('请输入 run_id')
      return
    }
    if (!scenarioVersionId) {
      toast.error('场景版本缺失，无法创建手工会话')
      return
    }
    setCreating(true)
    try {
      const created = await createManualSession(scenarioId, {
        run_id: runIdNum,
        scenario_version_id: scenarioVersionId,
      })
      setSession(created)
      toast.success(`手工会话 ${created.id} 已创建`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建手工会话失败')
    } finally {
      setCreating(false)
    }
  }

  const doAddStep = async () => {
    if (!session || adding) return
    setAdding(true)
    try {
      await addManualStep(scenarioId, session.id)
      const list = await fetchManualSteps(scenarioId, session.id)
      setSteps(list)
      toast.success('已添加步骤')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '添加步骤失败')
    } finally {
      setAdding(false)
    }
  }

  const doComplete = async (stepId: string, payload: CompleteManualStepInput) => {
    if (!session) return
    await completeManualStep(scenarioId, session.id, stepId, payload)
    toast.success(`步骤 ${stepId} 已更新`)
    setSteps(await fetchManualSteps(scenarioId, session.id))
  }

  const refreshSteps = async () => {
    if (!session) return
    setLoading(true)
    try {
      setSteps(await fetchManualSteps(scenarioId, session.id))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '刷新步骤失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>手工执行会话 (Assisted Manual)</CardTitle>
          <CardDescription>
            创建手工会话后逐步人工执行，并记录每条步骤的状态与备注。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {session ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-mono">{session.id}</span>
              <Badge tone="success">{session.status}</Badge>
              <Badge variant="outline">版本 {session.scenario_version_id}</Badge>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-[12rem_1fr]">
              <div className="space-y-1.5">
                <label htmlFor="manual-run-id" className="text-xs font-medium text-muted-foreground">run_id</label>
                <Input
                  id="manual-run-id"
                  type="number"
                  value={runId}
                  onChange={(e) => setRunId(e.target.value)}
                  placeholder="执行运行 ID"
                />
              </div>
              <div className="flex items-end">
                <Button onClick={doCreate} disabled={creating || !scenarioVersionId}>
                  <Play className="size-4" /> {creating ? '创建中…' : '创建手工会话'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {session && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>步骤清单</span>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={refreshSteps} disabled={loading}>
                  <RefreshCw className="size-3.5" /> 刷新
                </Button>
                <Button variant="secondary" size="sm" onClick={doAddStep} disabled={adding}>
                  <Plus className="size-3.5" /> {adding ? '添加中…' : '添加步骤'}
                </Button>
              </div>
            </CardTitle>
            <CardDescription>共 {steps.length} 条步骤</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-4 text-center text-sm text-muted-foreground">加载步骤中…</p>
            ) : steps.length === 0 ? (
              <p className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
                暂无步骤，点击「添加步骤」。
              </p>
            ) : (
              <div className="space-y-2">
                {steps.map((step) => (
                  <ManualStepItem key={step.id} step={step} onComplete={doComplete} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
