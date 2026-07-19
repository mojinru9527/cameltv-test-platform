import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { createTestCase, updateTestCase, reviewCase, fetchReviewHistory } from '@/api/testcase'
import { Code2, FileText } from '@/lib/icons'
import type { TestCaseReviewTransition } from '@/types'

const formSchema = z.object({
  title: z.string().min(1, '请输入标题'),
  case_id: z.string().optional().or(z.literal('')),
  case_type: z.enum(['manual', 'api', 'ui']).default('manual'),
  priority: z.enum(['P0', 'P1', 'P2', 'P3']).default('P2'),
  status: z.enum(['draft', 'active', 'archived']).default('active'),
  domain: z.string().optional().or(z.literal('')),
  module: z.string().optional().or(z.literal('')),
  api_method: z.string().optional().or(z.literal('')),
  api_endpoint: z.string().optional().or(z.literal('')),
  tags: z.string().optional().or(z.literal('')),
  preconditions: z.string().optional().or(z.literal('')),
  steps: z.string().optional().or(z.literal('')),
  expected_result: z.string().optional().or(z.literal('')),
  api_spec_ref: z.string().optional().or(z.literal('')),
})

type FormData = z.infer<typeof formSchema>

interface Props {
  open: boolean
  editing: any | null
  domains: any[]
  onClose: () => void
  onSaved: () => void
}

const CASE_TYPES = [
  { value: 'manual', label: '功能用例' },
  { value: 'api', label: '接口用例' },
  { value: 'ui', label: 'UI 用例' },
]

const PRIORITIES = [
  { value: 'P0', label: 'P0' },
  { value: 'P1', label: 'P1' },
  { value: 'P2', label: 'P2' },
  { value: 'P3', label: 'P3' },
]

const STATUSES = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '启用' },
  { value: 'archived', label: '归档' },
]

const REVIEW_LABELS: Record<string, string> = { draft: '草稿', submitted: '已提交', approved: '已通过', rejected: '已驳回' }
const REVIEW_COLORS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = { draft: 'secondary', submitted: 'outline', approved: 'default', rejected: 'destructive' }

export default function CaseDrawer({ open, editing, domains, onClose, onSaved }: Props) {
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('form')
  const [reviewComment, setReviewComment] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [reviewHistory, setReviewHistory] = useState<TestCaseReviewTransition[]>([])

  const {
    register,
    control,
    watch,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      case_type: 'manual',
      priority: 'P2',
      status: 'active',
    },
  })

  const selDomain = watch('domain')
  const selType = watch('case_type')

  useEffect(() => {
    if (open) {
      if (editing) {
        const vals: Record<string, any> = {}
        for (const key of Object.keys(formSchema.shape)) {
          if (editing[key] !== undefined && editing[key] !== null) {
            vals[key] = String(editing[key])
          }
        }
        reset(vals)
        setActiveTab('form')
        // Load review history
        loadReviewHistory(editing.id)
      } else {
        reset({
          case_type: 'manual',
          priority: 'P2',
          status: 'active',
        })
        setReviewHistory([])
        setActiveTab('form')
      }
    }
  }, [open, editing, reset])

  const loadReviewHistory = async (caseId: number) => {
    try {
      const h = await fetchReviewHistory(caseId)
      setReviewHistory(h || [])
    } catch { setReviewHistory([]) }
  }

  const selModules = domains
    .find((d: any) => d.domain === selDomain)?.modules
    ?.map((m: any) => ({ value: m.module, label: `${m.module}` })) || []

  useEffect(() => {
    if (selDomain && editing?.module) {
      // keep existing module if domain matches
    } else if (selDomain && !selModules.some((m: any) => m.value === watch('module'))) {
      setValue('module', '')
    }
  }, [selDomain])

  const doSave = async (data: FormData) => {
    setSaving(true)
    try {
      const body: Record<string, any> = { ...data }
      for (const key of Object.keys(body)) {
        if (body[key] === '') body[key] = undefined
      }
      if (editing?.id) {
        await updateTestCase(editing.id, body)
        toast.success('已更新')
      } else {
        await createTestCase(body)
        toast.success('已创建')
      }
      onSaved()
    } catch {
      // handled by interceptor
    } finally { setSaving(false) }
  }

  // ── Review actions ──

  const doReview = async (action: string) => {
    if (!editing?.id) return
    setReviewing(true)
    try {
      await reviewCase(editing.id, action, reviewComment)
      toast.success(
        action === 'submit' ? '已提交评审'
          : action === 'approve' ? '已通过'
          : action === 'reject' ? '已驳回'
          : '已撤回'
      )
      setReviewComment('')
      onSaved()
    } catch {
      // handled by interceptor
    } finally { setReviewing(false) }
  }

  const reviewStatus = editing?.review_status || 'draft'

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-[680px]">
        <DialogHeader>
          <DialogTitle>{editing?.id ? '编辑用例' : '新建用例'}</DialogTitle>
          <DialogDescription>
            {editing?.id ? '修改用例信息' : '创建一个新的测试用例'}
          </DialogDescription>
        </DialogHeader>

        {editing?.id ? (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="form">基本信息</TabsTrigger>
              <TabsTrigger value="review">评审</TabsTrigger>
            </TabsList>

            <TabsContent value="form">
              <CaseForm
                register={register} control={control} errors={errors}
                selDomain={selDomain} selType={selType}
                domains={domains} selModules={selModules}
                watch={watch} setValue={setValue}
              />
            </TabsContent>

            <TabsContent value="review">
              <ReviewPanel
                reviewStatus={reviewStatus}
                reviewComment={reviewComment}
                setReviewComment={setReviewComment}
                reviewing={reviewing}
                reviewHistory={reviewHistory}
                onReview={doReview}
              />
            </TabsContent>
          </Tabs>
        ) : (
          <form onSubmit={handleSubmit(doSave)} className="max-h-[60vh] overflow-y-auto space-y-4">
            <CaseForm
              register={register} control={control} errors={errors}
              selDomain={selDomain} selType={selType}
              domains={domains} selModules={selModules}
              watch={watch} setValue={setValue}
            />
          </form>
        )}

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" onClick={onClose}>取消</Button>
          </DialogClose>
          {activeTab === 'form' && (
            <Button disabled={saving} onClick={handleSubmit(doSave)}>
              {saving ? '保存中...' : '保存'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Sub-components ──

function CaseForm({ register, control, errors, selDomain, selType, domains, selModules, watch, setValue }: any) {
  const stepsValue = watch('steps') || ''
  const [stepsViewMode, setStepsViewMode] = useState<'formatted' | 'json'>('formatted')

  // Parse steps JSON to formatted text: "1、操作描述 — 预期结果"
  const formatSteps = (raw: string): string => {
    if (!raw || !raw.trim()) return ''
    try {
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return raw
      return parsed.map((s: any) => {
        const stepNum = s.step || ''
        const desc = s.desc || s.action || s.description || ''
        const expected = s.expected || ''
        return expected ? `${stepNum}、${desc} — ${expected}` : `${stepNum}、${desc}`
      }).join('\n')
    } catch {
      return raw
    }
  }

  return (
    <div className="max-h-[50vh] overflow-y-auto space-y-4">
      {/* Title */}
      <div>
        <label htmlFor="case-title" className="mb-1 block text-sm font-medium">标题</label>
        <Input
          id="case-title"
          placeholder="用例标题"
          {...register('title')}
          data-invalid={!!errors.title}
          aria-invalid={!!errors.title}
          aria-describedby={errors.title ? 'case-title-error' : undefined}
        />
        {errors.title && (
          <p id="case-title-error" className="mt-1 text-xs text-destructive">{errors.title.message}</p>
        )}
      </div>

      {/* Case ID */}
      <div>
        <label htmlFor="case-id" className="mb-1 block text-sm font-medium">用例编号</label>
        <Input id="case-id" placeholder="如 TC-HOME-001" {...register('case_id')} />
      </div>

      {/* Row: Type, Priority, Status */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label htmlFor="case-type" className="mb-1 block text-sm font-medium">用例类型</label>
          <Controller
            name="case_type"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="case-type" size="sm"><SelectValue placeholder="选择类型" /></SelectTrigger>
                <SelectContent>
                  {CASE_TYPES.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <div>
          <label htmlFor="case-priority" className="mb-1 block text-sm font-medium">优先级</label>
          <Controller
            name="priority"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="case-priority" size="sm"><SelectValue placeholder="优先级" /></SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <div>
          <label htmlFor="case-status" className="mb-1 block text-sm font-medium">状态</label>
          <Controller
            name="status"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="case-status" size="sm"><SelectValue placeholder="状态" /></SelectTrigger>
                <SelectContent>
                  {STATUSES.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
      </div>

      {/* Row: Domain, Module */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="case-domain" className="mb-1 block text-sm font-medium">所属域</label>
          <Controller
            name="domain"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id="case-domain" size="sm"><SelectValue placeholder="选择域" /></SelectTrigger>
                <SelectContent>
                  {domains.map((d: any) => (
                    <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <div>
          <label htmlFor="case-module" className="mb-1 block text-sm font-medium">所属模块</label>
          <Controller
            name="module"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id="case-module" size="sm"><SelectValue placeholder="选择模块" /></SelectTrigger>
                <SelectContent>
                  {selModules.map((m: any) => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
      </div>

      {/* Conditional API fields */}
      {selType === 'api' && (
        <div className="grid grid-cols-[120px_1fr] gap-4">
          <div>
            <label htmlFor="case-api-method" className="mb-1 block text-sm font-medium">HTTP 方法</label>
            <Controller
              name="api_method"
              control={control}
              render={({ field }: any) => (
                <Select value={field.value || undefined} onValueChange={field.onChange}>
                  <SelectTrigger id="case-api-method" size="sm"><SelectValue placeholder="方法" /></SelectTrigger>
                  <SelectContent>
                    {['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((v) => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>
          <div>
            <label htmlFor="case-api-endpoint" className="mb-1 block text-sm font-medium">接口路径</label>
            <Input id="case-api-endpoint" placeholder="/api/v1/xxx" {...register('api_endpoint')} />
          </div>
        </div>
      )}

      {/* Tags */}
      <div>
        <label htmlFor="case-tags" className="mb-1 block text-sm font-medium">标签 (JSON 数组)</label>
        <Input id="case-tags" placeholder='["功能","首页"]' {...register('tags')} />
      </div>

      {/* Preconditions */}
      <div>
        <label htmlFor="case-preconditions" className="mb-1 block text-sm font-medium">前置条件</label>
        <Textarea id="case-preconditions" rows={2} placeholder="执行用例前需要满足的条件" {...register('preconditions')} />
      </div>

      {/* Steps */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label htmlFor="case-steps" className="text-sm font-medium">测试步骤 (JSON)</label>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              size="sm"
              variant={stepsViewMode === 'formatted' ? 'default' : 'outline'}
              className="h-7 text-xs px-2"
              onClick={() => setStepsViewMode('formatted')}
            >
              <FileText className="size-3 mr-1" />
              格式化
            </Button>
            <Button
              type="button"
              size="sm"
              variant={stepsViewMode === 'json' ? 'default' : 'outline'}
              className="h-7 text-xs px-2"
              onClick={() => setStepsViewMode('json')}
            >
              <Code2 className="size-3 mr-1" />
              JSON
            </Button>
          </div>
        </div>
        {stepsViewMode === 'formatted' && stepsValue ? (
          <pre className="text-sm leading-relaxed bg-muted/30 rounded-md p-3 min-h-[120px] whitespace-pre-wrap font-sans">
            {formatSteps(stepsValue) || '暂无步骤'}
          </pre>
        ) : (
          <Textarea id="case-steps" rows={4} placeholder='[{"step":1,"desc":"操作描述","expected":"预期结果"}]' {...register('steps')} />
        )}
      </div>

      {/* Expected Result */}
      <div>
        <label htmlFor="case-expected-result" className="mb-1 block text-sm font-medium">预期结果</label>
        <Textarea id="case-expected-result" rows={2} placeholder="整体预期结果描述" {...register('expected_result')} />
      </div>

      {/* Ref */}
      <div>
        <label htmlFor="case-api-spec-ref" className="mb-1 block text-sm font-medium">关联引用</label>
        <Input id="case-api-spec-ref" placeholder="generated:Module:spec 或 functional:Suite:ID" {...register('api_spec_ref')} />
      </div>
    </div>
  )
}

function ReviewPanel({
  reviewStatus, reviewComment, setReviewComment, reviewing,
  reviewHistory, onReview,
}: {
  reviewStatus: string
  reviewComment: string
  setReviewComment: (v: string) => void
  reviewing: boolean
  reviewHistory: TestCaseReviewTransition[]
  onReview: (action: string) => void
}) {
  const statusLabel = REVIEW_LABELS[reviewStatus] || reviewStatus
  const statusColor = REVIEW_COLORS[reviewStatus] || 'secondary'

  return (
    <div className="max-h-[50vh] overflow-y-auto space-y-4">
      {/* Current status */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">当前评审状态：</span>
        <Badge variant={statusColor}>{statusLabel}</Badge>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {(reviewStatus === 'draft' || reviewStatus === 'rejected') && (
          <Button size="sm" onClick={() => onReview('submit')} disabled={reviewing}>
            {reviewing ? '提交中...' : '提交评审'}
          </Button>
        )}
        {reviewStatus === 'submitted' && (
          <>
            <Button size="sm" variant="default" onClick={() => onReview('approve')} disabled={reviewing}>
              {reviewing ? '处理中...' : '通过'}
            </Button>
            <Button size="sm" variant="destructive" onClick={() => onReview('reject')} disabled={reviewing}>
              {reviewing ? '处理中...' : '驳回'}
            </Button>
            <Button size="sm" variant="outline" onClick={() => onReview('withdraw')} disabled={reviewing}>
              撤回
            </Button>
          </>
        )}
        {reviewStatus === 'approved' && (
          <p className="text-sm text-muted-foreground">此用例已评审通过。修改用例内容将重置评审状态为草稿。</p>
        )}
      </div>

      {/* Comment */}
      {reviewStatus !== 'approved' && (
        <div>
          <label htmlFor="review-comment" className="mb-1 block text-sm font-medium">评审意见</label>
          <Textarea
            id="review-comment"
            rows={3}
            placeholder="输入评审意见（可选）"
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
          />
        </div>
      )}

      {/* Review history */}
      <div>
        <h4 className="text-sm font-semibold mb-2">评审历史</h4>
        {reviewHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无评审记录</p>
        ) : (
          <div className="space-y-2">
            {reviewHistory.map((t) => (
              <div key={t.id} className="rounded-md border p-3 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={REVIEW_COLORS[t.from_status] || 'secondary'} className="text-[10px]">
                    {t.from_label}
                  </Badge>
                  <span className="text-muted-foreground">→</span>
                  <Badge variant={REVIEW_COLORS[t.to_status] || 'default'} className="text-[10px]">
                    {t.to_label}
                  </Badge>
                  <span className="text-muted-foreground ml-auto text-xs">
                    {t.reviewer_name} · {t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : ''}
                  </span>
                </div>
                {t.comment && (
                  <p className="text-muted-foreground text-xs mt-1">意见: {t.comment}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
