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
import { createPlan, updatePlan } from '@/api/testplan'
import { fetchUsers } from '@/api/system'

const formSchema = z.object({
  name: z.string().min(1, '请输入计划名称'),
  plan_id: z.string().optional().or(z.literal('')),
  description: z.string().optional().or(z.literal('')),
  status: z.enum(['draft', 'active', 'completed', 'archived']).default('draft'),
  assignee_id: z.coerce.number().optional().or(z.literal(0)),
  start_date: z.string().optional().or(z.literal('')),
  end_date: z.string().optional().or(z.literal('')),
  due_date: z.string().optional().or(z.literal('')),
})

type FormData = z.infer<typeof formSchema>

interface Props {
  open: boolean
  editing: any | null
  onClose: () => void
  onSaved: () => void
}

const STATUSES = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'archived', label: '已归档' },
]

function isoToDatetimeLocal(iso?: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return ''
  }
}

export default function PlanDrawer({ open, editing, onClose, onSaved }: Props) {
  const [saving, setSaving] = useState(false)
  const [users, setUsers] = useState<any[]>([])

  useEffect(() => {
    fetchUsers().then((d: any) => setUsers(d || [])).catch(() => {})
  }, [])

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      status: 'draft',
    },
  })

  useEffect(() => {
    if (open) {
      if (editing) {
        reset({
          name: editing.name || '',
          plan_id: editing.plan_id || '',
          description: editing.description || '',
          status: editing.status || 'draft',
          assignee_id: editing.assignee_id || 0,
          start_date: isoToDatetimeLocal(editing.start_date),
          end_date: isoToDatetimeLocal(editing.end_date),
          due_date: isoToDatetimeLocal(editing.due_date),
        })
      } else {
        reset({
          status: 'draft',
          assignee_id: 0,
        })
      }
    }
  }, [open, editing, reset])

  const doSave = async (data: FormData) => {
    setSaving(true)
    try {
      const body: Record<string, any> = {
        ...data,
        assignee_id: data.assignee_id || null,
        start_date: data.start_date ? new Date(data.start_date).toISOString() : undefined,
        end_date: data.end_date ? new Date(data.end_date).toISOString() : undefined,
        due_date: data.due_date ? new Date(data.due_date).toISOString() : undefined,
      }
      if (editing?.id) {
        await updatePlan(editing.id, body)
        toast.success('已更新')
      } else {
        await createPlan(body)
        toast.success('已创建')
      }
      onSaved()
    } catch {
      // handled by interceptor
    } finally { setSaving(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle>{editing?.id ? '编辑计划' : '新建计划'}</DialogTitle>
          <DialogDescription>
            {editing?.id ? '修改测试计划信息' : '创建一个新的测试计划'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(doSave)} className="max-h-[60vh] overflow-y-auto space-y-4">
          {/* Name */}
          <div>
            <label htmlFor="plan-name" className="mb-1 block text-sm font-medium">计划名称</label>
            <Input
              id="plan-name"
              placeholder="如：回归测试 v1.0"
              {...register('name')}
              data-invalid={!!errors.name}
              aria-invalid={!!errors.name}
              aria-describedby={errors.name ? 'plan-name-error' : undefined}
            />
            {errors.name && (
              <p id="plan-name-error" className="mt-1 text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>

          {/* Plan ID */}
          <div>
            <label htmlFor="plan-id" className="mb-1 block text-sm font-medium">计划编号</label>
            <Input id="plan-id" placeholder="如 TP-HOME-001 (可选)" {...register('plan_id')} />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="plan-description" className="mb-1 block text-sm font-medium">计划描述</label>
            <Textarea id="plan-description" rows={3} placeholder="测试范围、目标、注意事项等" {...register('description')} />
          </div>

          {/* Row: Assignee, Due Date */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="plan-assignee" className="mb-1 block text-sm font-medium">负责人</label>
              <Controller
                name="assignee_id"
                control={control}
                render={({ field }) => (
                  <Select
                    value={String(field.value || 0)}
                    onValueChange={(v) => field.onChange(Number(v))}
                  >
                    <SelectTrigger id="plan-assignee" size="sm">
                      <SelectValue placeholder="选择负责人（可选）" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">-</SelectItem>
                      {users.map((u: any) => (
                        <SelectItem key={u.id} value={String(u.id)}>
                          {u.nickname || u.username || u.id}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div>
              <label htmlFor="plan-due-date" className="mb-1 block text-sm font-medium">截止日期</label>
              <Input id="plan-due-date" type="datetime-local" {...register('due_date')} />
            </div>
          </div>

          {/* Row: Status, Start Date, End Date */}
          <div className="grid grid-cols-[140px_1fr_1fr] gap-4">
            <div>
              <label htmlFor="plan-status" className="mb-1 block text-sm font-medium">状态</label>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="plan-status" size="sm">
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
            <div>
              <label htmlFor="plan-start-date" className="mb-1 block text-sm font-medium">开始时间</label>
              <Input id="plan-start-date" type="datetime-local" {...register('start_date')} />
            </div>
            <div>
              <label htmlFor="plan-end-date" className="mb-1 block text-sm font-medium">结束时间</label>
              <Input id="plan-end-date" type="datetime-local" {...register('end_date')} />
            </div>
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
