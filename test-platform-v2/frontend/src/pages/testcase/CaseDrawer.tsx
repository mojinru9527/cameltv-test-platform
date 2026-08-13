import { useEffect, useMemo, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import AssertionEditor from '@/pages/apitest/components/AssertionEditor'
import { z } from 'zod'
import { toast } from 'sonner'

import { Button } from '@/ui'
import { Input } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/ui'
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
import { fetchDatasets } from '@/api/dataset'
import { Code2, FileText } from '@/lib/icons'
import type { TestCaseReviewTransition } from '@/types'

const formSchema = z.object({
  title: z.string().min(1, '请输入标题'),
  case_type: z.enum(['manual', 'api', 'ui']).default('manual'),
  priority: z.enum(['P0', 'P1', 'P2', 'P3']).default('P2'),
  status: z.enum(['draft', 'active', 'archived']).default('active'),
  domain: z.string().min(1, '请选择域'),
  module: z.string().min(1, '请选择模块'),
  api_method: z.string().optional().or(z.literal('')),
  api_endpoint: z.string().optional().or(z.literal('')),
  api_body: z.string().optional().or(z.literal('')),
  api_assertions: z.string().optional().or(z.literal('')),
  dataset_id: z.number().nullable().optional().default(null),
  case_design_method: z.string().optional().or(z.literal('')),
  positive_negative: z.string().optional().or(z.literal('')),
  test_data_note: z.string().optional().or(z.literal('')),
  preconditions: z.string().optional().or(z.literal('')),
  steps: z.string().min(1, '请输入测试步骤'),
  expected_result: z.string().min(1, '请输入预期结果'),
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
const REVIEW_TONES: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  draft: 'neutral',
  submitted: 'info',
  approved: 'success',
  rejected: 'danger',
}

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
      title: '',
      case_type: 'manual',
      priority: 'P2',
      status: 'active',
      domain: '',
      module: '',
      steps: '',
      expected_result: '',
      dataset_id: null,
    },
  })

  const selDomain = watch('domain')
  const selType = watch('case_type')
  const [datasets, setDatasets] = useState<any[]>([])

  useEffect(() => {
    if (open) {
      fetchDatasets({ page_size: 100 }).then((d: any) => setDatasets(d?.items || [])).catch(() => {})
      if (editing) {
        const vals: Record<string, any> = {}
        for (const key of Object.keys(formSchema.shape)) {
          if (editing[key] !== undefined && editing[key] !== null) {
            vals[key] = key === 'dataset_id' ? editing[key] : String(editing[key])
          }
        }
        reset(vals)
        setActiveTab('form')
        // Load review history
        loadReviewHistory(editing.id)
      } else {
        reset({
          title: '',
          case_type: 'manual',
          priority: 'P2',
          status: 'active',
          domain: '',
          module: '',
          steps: '',
          expected_result: '',
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

  const selectedDomain = useMemo(
    () => domains.find((d: any) => d.domain === selDomain),
    [domains, selDomain],
  )
  const selModules = useMemo(
    () => selectedDomain?.modules
      ?.map((m: any) => ({ value: m.module, label: `${m.module}` })) || [],
    [selectedDomain],
  )
  const selectedModule = watch('module')

  useEffect(() => {
    if (
      selDomain
      && selectedDomain
      && selectedModule
      && !selModules.some((m: any) => m.value === selectedModule)
    ) {
      setValue('module', '')
    }
  }, [selDomain, selectedDomain, selectedModule, selModules, setValue])

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
              {editing?.case_type === 'api' && <TabsTrigger value="api-data">接口数据</TabsTrigger>}
              <TabsTrigger value="review">评审</TabsTrigger>
            </TabsList>

            <TabsContent value="form">
              <CaseForm
                register={register} control={control} errors={errors}
                selDomain={selDomain} selType={selType}
                domains={domains} selModules={selModules}
                watch={watch} setValue={setValue}
              datasets={datasets} />
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

            {editing?.case_type === 'api' && (
              <TabsContent value="api-data">
                <ApiDataPanel editing={editing} />
              </TabsContent>
            )}
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
            <Button variant="secondary" onClick={onClose}>取消</Button>
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

function CaseForm({ register, control, errors, selType, domains, selModules, watch, setValue, datasets }: any) {
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
    <div className="max-h-[60vh] overflow-y-auto space-y-4">
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
                <SelectContent position="popper">
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
                <SelectContent position="popper">
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
                <SelectContent position="popper">
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
                <SelectContent position="popper">
                  {domains.map((d: any) => (
                    <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          {errors.domain && (
            <p className="mt-1 text-xs text-destructive" role="alert">{errors.domain.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="case-module" className="mb-1 block text-sm font-medium">所属模块 <span className="text-destructive">*</span></label>
          <Controller
            name="module"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id="case-module" size="sm"><SelectValue placeholder="选择模块" /></SelectTrigger>
                <SelectContent position="popper">
                  {selModules.map((m: any) => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          {errors.module && (
            <p className="mt-1 text-xs text-destructive" role="alert">{errors.module.message}</p>
          )}
        </div>
      </div>

      {/* Conditional API fields */}
      {selType === 'api' && (
        <>
          <div className="grid grid-cols-[120px_1fr] gap-4">
            <div>
              <label htmlFor="case-api-method" className="mb-1 block text-sm font-medium">HTTP 方法</label>
              <Controller
                name="api_method"
                control={control}
                render={({ field }: any) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger id="case-api-method" size="sm"><SelectValue placeholder="方法" /></SelectTrigger>
                    <SelectContent position="popper">
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

          {/* C147-8: 数据集参数化绑定 */}
          <div className="grid grid-cols-[180px_1fr] gap-4">
            <div>
              <label htmlFor="case-dataset" className="mb-1 block text-sm font-medium">默认数据集</label>
              <Controller
                name="dataset_id"
                control={control}
                render={({ field }: any) => (
                  <Select
                    value={field.value == null ? '__none__' : String(field.value)}
                    onValueChange={(v) => field.onChange(v === '__none__' ? null : Number(v))}
                  >
                    <SelectTrigger id="case-dataset" size="sm"><SelectValue placeholder="未绑定（${列名} 替换需选数据集）" /></SelectTrigger>
                    <SelectContent position="popper">
                      <SelectItem value="__none__">未绑定</SelectItem>
                      {datasets.map((d: any) => (
                        <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="flex items-end pb-1">
              <p className="text-xs text-muted-foreground">执行时按数据集逐行替换请求中的 {'${列名}'} 变量</p>
            </div>
          </div>

          {/* 设计方法 / 正负向 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="case-design-method" className="mb-1 block text-sm font-medium">设计方法</label>
              <Controller
                name="case_design_method"
                control={control}
                render={({ field }: any) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger id="case-design-method" size="sm"><SelectValue placeholder="选择设计方法" /></SelectTrigger>
                    <SelectContent position="popper">
                      {['等价类划分', '边界值分析', '场景法', '错误推测', '组合覆盖'].map((v) => (
                        <SelectItem key={v} value={v}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div>
              <label htmlFor="case-positive-negative" className="mb-1 block text-sm font-medium">正负向/边界</label>
              <Controller
                name="positive_negative"
                control={control}
                render={({ field }: any) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger id="case-positive-negative" size="sm"><SelectValue placeholder="选择类型" /></SelectTrigger>
                    <SelectContent position="popper">
                      <SelectItem value="positive">正向</SelectItem>
                      <SelectItem value="negative">负向</SelectItem>
                      <SelectItem value="boundary">边界</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          {/* 请求参数 */}
          <div>
            <label htmlFor="case-api-body" className="mb-1 block text-sm font-medium">
              请求参数（JSON，字段完整、值贴合真实业务）
            </label>
            <Textarea
              id="case-api-body"
              rows={5}
              placeholder='{"page": 1, "size": 30, "queryList": [], "locale": "en"}'
              {...register('api_body')}
            />
          </div>

          {/* (batch-165) 断言改为结构化编辑器（与执行引擎 status_code/jsonpath/regex/response_time/header/type/array_length/json_schema 兼容） */}
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="case-api-assertions" className="text-sm font-medium">断言规则</label>
              <span className="text-xs text-muted-foreground">保存后执行时按规则校验响应</span>
            </div>
            <Controller
              name="api_assertions"
              control={control}
              render={({ field }: any) => (
                <AssertionEditor value={field.value || '[]'} onChange={field.onChange} />
              )}
            />
          </div>

          {/* 数据说明 */}
          <div>
            <label htmlFor="case-test-data-note" className="mb-1 block text-sm font-medium">数据说明（业务含义/来源）</label>
            <Textarea
              id="case-test-data-note"
              rows={2}
              placeholder="本用例输入数据的业务含义与来源（真实回填或按语义构造）"
              {...register('test_data_note')}
            />
          </div>
        </>
      )}

      {/* Preconditions */}
      <div>
        <label htmlFor="case-preconditions" className="mb-1 block text-sm font-medium">前置条件</label>
        <Textarea id="case-preconditions" rows={2} placeholder="执行用例前需要满足的条件" {...register('preconditions')} />
      </div>

      {/* Steps */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label htmlFor="case-steps" className="text-sm font-medium">测试步骤</label>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              size="sm"
              variant={stepsViewMode === 'formatted' ? 'primary' : 'secondary'}
              className="h-7 text-xs px-2"
              onClick={() => setStepsViewMode('formatted')}
            >
              <FileText className="size-3 mr-1" />
              格式化
            </Button>
            <Button
              type="button"
              size="sm"
              variant={stepsViewMode === 'json' ? 'primary' : 'secondary'}
              className="h-7 text-xs px-2"
              onClick={() => setStepsViewMode('json')}
            >
              <Code2 className="size-3 mr-1" />
              JSON
            </Button>
          </div>
        </div>
        {stepsViewMode === 'formatted' ? (
          <Textarea
            id="case-steps"
            rows={4}
            placeholder="逐行输入测试步骤"
            value={formatSteps(stepsValue)}
            onChange={(event) => setValue('steps', event.target.value, {
              shouldDirty: true,
              shouldValidate: true,
            })}
            aria-invalid={!!errors.steps}
            aria-describedby={errors.steps ? 'case-steps-error' : undefined}
          />
        ) : (
          <Textarea
            id="case-steps"
            rows={4}
            placeholder='[{"step":1,"desc":"操作描述","expected":"预期结果"}]'
            {...register('steps')}
            aria-invalid={!!errors.steps}
            aria-describedby={errors.steps ? 'case-steps-error' : undefined}
          />
        )}
        {errors.steps && (
          <p id="case-steps-error" className="mt-1 text-xs text-destructive" role="alert">
            {errors.steps.message}
          </p>
        )}
      </div>

      {/* Expected Result */}
      <div>
        <label htmlFor="case-expected-result" className="mb-1 block text-sm font-medium">预期结果</label>
        <Textarea
          id="case-expected-result"
          rows={2}
          placeholder="整体预期结果描述"
          {...register('expected_result')}
          aria-invalid={!!errors.expected_result}
          aria-describedby={errors.expected_result ? 'case-expected-result-error' : undefined}
        />
        {errors.expected_result && (
          <p id="case-expected-result-error" className="mt-1 text-xs text-destructive" role="alert">
            {errors.expected_result.message}
          </p>
        )}
      </div>

      {/* Ref */}
    </div>
  )
}

function ApiDataPanel({ editing }: { editing: any }) {
  const pretty = (raw: string | undefined, fallback: string) => {
    if (!raw) return fallback
    try {
      return JSON.stringify(JSON.parse(raw), null, 2)
    } catch {
      return raw
    }
  }
  const runStatus = editing?.last_run_status
  const runTone = runStatus === 'success' ? 'success' : runStatus === 'error' ? 'danger' : runStatus === 'fail' ? 'danger' : 'neutral'
  const runLabel = runStatus === 'success' ? '成功' : runStatus === 'fail' ? '失败' : runStatus === 'error' ? '错误' : '未执行'

  return (
    <div className="max-h-[60vh] space-y-4 overflow-y-auto">
      <div className="flex flex-wrap items-center gap-2">
        {editing?.case_design_method && (
          <Badge tone="info">设计方法：{editing.case_design_method}</Badge>
        )}
        {editing?.positive_negative && (
          <Badge tone={editing.positive_negative === 'positive' ? 'success' : editing.positive_negative === 'boundary' ? 'warning' : 'danger'}>
            {editing.positive_negative === 'positive' ? '正向' : editing.positive_negative === 'boundary' ? '边界' : '负向'}
          </Badge>
        )}
        <Badge tone={runTone as any}>最近执行：{runLabel}</Badge>
      </div>

      {editing?.test_data_note && (
        <div className="rounded-md border p-3 text-sm">
          <p className="mb-1 font-medium">数据说明</p>
          <p className="text-muted-foreground whitespace-pre-wrap">{editing.test_data_note}</p>
        </div>
      )}

      <div>
        <p className="mb-1 text-sm font-medium">请求参数</p>
        <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
          {pretty(editing?.api_body, '（空）')}
        </pre>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">断言</p>
        <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
          {pretty(editing?.api_assertions, '（空）')}
        </pre>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">请求结果（最近执行回填）</p>
        <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
          {pretty(editing?.last_response_json, '（尚未执行）')}
        </pre>
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
  const statusTone = REVIEW_TONES[reviewStatus] || 'neutral'

  return (
    <div className="max-h-[60vh] overflow-y-auto space-y-4">
      {/* Current status */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">当前评审状态：</span>
        <Badge tone={statusTone}>{statusLabel}</Badge>
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
            <Button size="sm" variant="primary" onClick={() => onReview('approve')} disabled={reviewing}>
              {reviewing ? '处理中...' : '通过'}
            </Button>
            <Button size="sm" variant="danger" onClick={() => onReview('reject')} disabled={reviewing}>
              {reviewing ? '处理中...' : '驳回'}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onReview('withdraw')} disabled={reviewing}>
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
                  <Badge tone={REVIEW_TONES[t.from_status] || 'neutral'} className="text-xs">
                    {t.from_label}
                  </Badge>
                  <span className="text-muted-foreground">→</span>
                  <Badge tone={REVIEW_TONES[t.to_status] || 'neutral'} className="text-xs">
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
