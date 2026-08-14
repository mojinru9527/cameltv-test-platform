import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { Button } from '@/ui'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { createTestCase, updateTestCase, reviewCase, fetchReviewHistory } from '@/api/testcase'
import { fetchDatasets } from '@/api/dataset'
import CaseForm from './components/CaseForm'
import ApiDataPanel from './components/ApiDataPanel'
import ReviewPanel from './components/ReviewPanel'
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
    if (!open) return
    let cancelled = false
    fetchDatasets({ page_size: 100 }).then((d: any) => { if (!cancelled) setDatasets(d?.items || []) }).catch(() => {})
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
      loadReviewHistory(editing.id, () => cancelled)
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
    return () => { cancelled = true }
  }, [open, editing, reset])

  const loadReviewHistory = async (caseId: number, isCancelled?: () => boolean) => {
    try {
      const h = await fetchReviewHistory(caseId)
      if (!isCancelled?.()) setReviewHistory(h || [])
    } catch { if (!isCancelled?.()) setReviewHistory([]) }
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
