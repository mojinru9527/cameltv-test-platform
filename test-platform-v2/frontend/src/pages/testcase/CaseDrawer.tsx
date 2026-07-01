import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
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
import { createTestCase, updateTestCase } from '@/api/testcase'

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

export default function CaseDrawer({ open, editing, domains, onClose, onSaved }: Props) {
  const [saving, setSaving] = useState(false)

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
      } else {
        reset({
          case_type: 'manual',
          priority: 'P2',
          status: 'active',
        })
      }
    }
  }, [open, editing, reset])

  const selModules = domains
    .find((d: any) => d.domain === selDomain)?.modules
    ?.map((m: any) => ({ value: m.module, label: `${m.module}` })) || []

  // Reset module when domain changes
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
      // Remove empty strings to send as undefined
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

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-[680px]">
        <DialogHeader>
          <DialogTitle>{editing?.id ? '编辑用例' : '新建用例'}</DialogTitle>
          <DialogDescription>
            {editing?.id ? '修改用例信息' : '创建一个新的测试用例'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(doSave)} className="max-h-[60vh] overflow-y-auto space-y-4">
          {/* Title */}
          <div>
            <label className="mb-1 block text-sm font-medium">标题</label>
            <Input
              placeholder="用例标题"
              {...register('title')}
              data-invalid={!!errors.title}
              aria-invalid={!!errors.title}
            />
            {errors.title && (
              <p className="mt-1 text-xs text-destructive">{errors.title.message}</p>
            )}
          </div>

          {/* Case ID */}
          <div>
            <label className="mb-1 block text-sm font-medium">用例编号</label>
            <Input placeholder="如 TC-HOME-001" {...register('case_id')} />
          </div>

          {/* Row: Type, Priority, Status */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">用例类型</label>
              <Controller
                name="case_type"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger size="sm">
                      <SelectValue placeholder="选择类型" />
                    </SelectTrigger>
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
              <label className="mb-1 block text-sm font-medium">优先级</label>
              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger size="sm">
                      <SelectValue placeholder="优先级" />
                    </SelectTrigger>
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
              <label className="mb-1 block text-sm font-medium">状态</label>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger size="sm">
                      <SelectValue placeholder="状态" />
                    </SelectTrigger>
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
              <label className="mb-1 block text-sm font-medium">所属域</label>
              <Controller
                name="domain"
                control={control}
                render={({ field }) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger size="sm">
                      <SelectValue placeholder="选择域" />
                    </SelectTrigger>
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
              <label className="mb-1 block text-sm font-medium">所属模块</label>
              <Controller
                name="module"
                control={control}
                render={({ field }) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger size="sm">
                      <SelectValue placeholder="选择模块" />
                    </SelectTrigger>
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
                <label className="mb-1 block text-sm font-medium">HTTP 方法</label>
                <Controller
                  name="api_method"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <SelectTrigger size="sm">
                        <SelectValue placeholder="方法" />
                      </SelectTrigger>
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
                <label className="mb-1 block text-sm font-medium">接口路径</label>
                <Input placeholder="/api/v1/xxx" {...register('api_endpoint')} />
              </div>
            </div>
          )}

          {/* Tags */}
          <div>
            <label className="mb-1 block text-sm font-medium">标签 (JSON 数组)</label>
            <Input placeholder='["功能","首页"]' {...register('tags')} />
          </div>

          {/* Preconditions */}
          <div>
            <label className="mb-1 block text-sm font-medium">前置条件</label>
            <Textarea rows={2} placeholder="执行用例前需要满足的条件" {...register('preconditions')} />
          </div>

          {/* Steps */}
          <div>
            <label className="mb-1 block text-sm font-medium">测试步骤 (JSON)</label>
            <Textarea rows={4} placeholder='[{"step":1,"desc":"操作描述","expected":"预期结果"}]' {...register('steps')} />
          </div>

          {/* Expected Result */}
          <div>
            <label className="mb-1 block text-sm font-medium">预期结果</label>
            <Textarea rows={2} placeholder="整体预期结果描述" {...register('expected_result')} />
          </div>

          {/* Ref */}
          <div>
            <label className="mb-1 block text-sm font-medium">关联引用</label>
            <Input placeholder="generated:Module:spec 或 functional:Suite:ID" {...register('api_spec_ref')} />
          </div>
        </form>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" onClick={onClose}>取消</Button>
          </DialogClose>
          <Button disabled={saving} onClick={handleSubmit(doSave)}>
            {saving ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
