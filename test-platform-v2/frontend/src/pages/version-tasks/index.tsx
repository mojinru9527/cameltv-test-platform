import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { ArrowRight } from 'lucide-react'
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, PageShell, Progress, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from '@/ui'
import {
  createVersionTask,
  generatePlanAi,
  getPlan,
  reviewPlanItem,
  transitionVersionTask,
  type PlanItem,
  type VersionTask,
} from '@/api/versionTask'
import { fetchRequirements } from '@/api/requirement'
import type { RequirementDocumentBrief } from '@/types'
import { toast } from 'sonner'

type Step = 1 | 2 | 3

/** B7 建任务向导：拖入需求 → 可审方案 → 逐条确认（无引擎术语）。 */
export default function VersionTasksPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>(1)
  const [title, setTitle] = useState('')
  const [version, setVersion] = useState('')
  const [modules, setModules] = useState('')
  const [requirementId, setRequirementId] = useState('__none__')
  const [requirements, setRequirements] = useState<RequirementDocumentBrief[]>([])
  const [requirementsError, setRequirementsError] = useState('')
  const [task, setTask] = useState<VersionTask | null>(null)
  const [plan, setPlan] = useState<PlanItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchRequirements({ page: 1, page_size: 100 })
      .then((result) => {
        if (!cancelled) setRequirements(result.items)
      })
      .catch((error: Error) => {
        if (!cancelled) setRequirementsError(error.message || '需求文档加载失败')
      })
    return () => { cancelled = true }
  }, [])

  async function handleCreate() {
    if (!title.trim() || !version.trim()) {
      toast.error('请输入任务标题与版本号')
      return
    }
    setLoading(true)
    try {
      const scopeModules = modules.split(',').map((m) => m.trim()).filter(Boolean)
      const created = await createVersionTask({
        title: title.trim(),
        version: version.trim(),
        requirement_doc_id: requirementId === '__none__' ? null : Number(requirementId),
        scope: { modules: scopeModules },
      })
      setTask(created)
      toast.success('版本验收任务已创建')
      setStep(2)
    } catch (e) {
      toast.error((e as Error).message || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleGeneratePlan() {
    if (!task) return
    setLoading(true)
    try {
      const items = await generatePlanAi(task.id)
      setPlan(items)
      if (items.length === 0) toast.error('AI 未返回有效方案，请检查项目 AI 配置')
      else toast.success('已生成验收方案，请逐条审核')
    } catch (e) {
      toast.error((e as Error).message || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleReview(itemId: number, action: string, patch: Record<string, unknown> = {}) {
    if (!task) return
    try {
      await reviewPlanItem(task.id, itemId, action, patch)
      setPlan(await getPlan(task.id))
      toast.success(`已${action === 'adopt' ? '采纳' : action === 'remove' ? '删除' : action === 'ask' ? '追问' : '修改'}`)
    } catch (e) {
      toast.error((e as Error).message || '操作失败')
    }
  }

  async function handleConfirm() {
    if (!task) return
    setLoading(true)
    try {
      const updated = await transitionVersionTask(task.id, 'plan_review')
      setTask(updated)
      toast.success('方案已确认，进入待审')
      setStep(3)
    } catch (e) {
      toast.error((e as Error).message || '确认失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageShell title="版本验收 · 建任务">
      <Card>
        <CardHeader>
          <CardTitle>版本验收 · 建任务</CardTitle>
          <CardDescription>三步走：填需求 → 审方案 → 下结论（无引擎术语）</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {(['建任务', '审方案', '确认'] as const).map((label, i) => (
              <div key={label} className="flex items-center gap-2">
                <Badge variant={step === i + 1 ? 'default' : 'secondary'}>{i + 1}</Badge>
                <span>{label}</span>
                {i < 2 && <span className="text-muted-foreground">→</span>}
              </div>
            ))}
          </div>

          {step === 1 && (
            <div className="space-y-3">
              <div className="space-y-1">
                <Label>任务标题</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="如：v2.6 提测验收" />
              </div>
              <div className="space-y-1">
                <Label>版本号</Label>
                <Input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="如：2.6.0" />
              </div>
              <div className="space-y-1">
                <Label>变更模块（逗号分隔）</Label>
                <Textarea value={modules} onChange={(e) => setModules(e.target.value)} placeholder="登录, 支付, 订单" />
              </div>
              <div className="space-y-1">
                <Label htmlFor="version-task-requirement">关联需求文档</Label>
                <Select value={requirementId} onValueChange={setRequirementId}>
                  <SelectTrigger id="version-task-requirement" aria-label="关联需求文档">
                    <SelectValue placeholder="选择需求文档" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">不关联需求文档</SelectItem>
                    {requirements.map((doc) => (
                      <SelectItem key={doc.id} value={String(doc.id)}>{doc.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {requirementsError && <p className="text-xs text-destructive">{requirementsError}</p>}
              </div>
              <Button variant="primary" onClick={handleCreate} disabled={loading}>创建任务</Button>
            </div>
          )}

          {step === 2 && task && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-sm">
                  <span className="font-medium">{task.title}</span> <Badge variant="secondary">{task.version}</Badge>
                </div>
                <Button variant="secondary" onClick={handleGeneratePlan} disabled={loading}>生成验收方案</Button>
              </div>
              {plan.length === 0 && <p className="text-sm text-muted-foreground">点击「生成验收方案」，AI 会基于需求产出可审条目。</p>}
              <div className="space-y-2">
                {plan.map((item) => (
                  <div key={item.id} className="rounded border p-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{item.item_type}</Badge>
                      <span className="font-medium">{item.title}</span>
                      <span className="ml-auto text-xs text-muted-foreground">置信度 {item.confidence}%</span>
                    </div>
                    <Progress value={item.confidence} className="mt-2 h-1" />
                    <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
                    {item.question && <p className="mt-1 text-xs text-muted-foreground">待确认：{item.question}</p>}
                    <div className="mt-2 flex gap-1">
                      <Button size="sm" variant={item.status === 'adopted' ? 'primary' : 'secondary'} onClick={() => handleReview(item.id, 'adopt')}>采纳</Button>
                      <Button size="sm" variant="ghost" onClick={() => { const answer = window.prompt('修改/追问说明（留空仅采纳）') ?? ''; if (answer) void handleReview(item.id, 'modify', { title: item.title, question: answer }) }}>修改</Button>
                      <Button size="sm" variant="ghost" onClick={() => { const q = window.prompt('待确认问题') ?? ''; if (q) void handleReview(item.id, 'ask', { question: q }) }}>追问</Button>
                      <Button size="sm" variant="danger" onClick={() => handleReview(item.id, 'remove')}>删除</Button>
                    </div>
                  </div>
                ))}
              </div>
              <Button variant="primary" onClick={handleConfirm} disabled={loading || plan.length === 0}>确认并进入待审</Button>
            </div>
          )}

          {step === 3 && task && (
            <div className="space-y-3">
              <p className="text-sm">方案已确认，任务状态：<Badge variant="default">{task.status}</Badge>（待评审）。</p>
              <Button variant="primary" onClick={() => navigate(`/version-tasks/${task.id}`)}>
                进入执行与证据
                <ArrowRight className="size-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </PageShell>
  )
}
