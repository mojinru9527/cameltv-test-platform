import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Loader2 } from '@/lib/icons'
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
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { createDefect, updateDefect } from '@/api/defect'
import { fetchTestCases } from '@/api/testcase'
import { fetchUsers } from '@/api/system'
import type { DefectItem } from '@/types'
import { SEVERITY_MAP, STATUS_MAP } from './constants'

const defectFormSchema = z.object({
  title: z.string().min(1, '请输入标题'),
  description: z.string().optional().default(''),
  severity: z.string().default('P2'),
  status: z.string().optional(),
  assignee_id: z.coerce.number().nullable().optional(),
  case_id: z.coerce.number().nullable().optional(),
  external_id: z.string().optional().default(''),
  external_url: z.string().optional().default(''),
})

type DefectFormValues = z.infer<typeof defectFormSchema>

interface DefectFormDialogProps {
  open: boolean
  editing: DefectItem | null
  onClose: () => void
  onSaved: () => void
}

export default function DefectFormDialog({ open, editing, onClose, onSaved }: DefectFormDialogProps) {
  const [saving, setSaving] = useState(false)
  const [users, setUsers] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])

  const form = useForm<DefectFormValues>({
    resolver: zodResolver(defectFormSchema),
    defaultValues: { title: '', description: '', severity: 'P2', status: undefined, assignee_id: null, case_id: null, external_id: '', external_url: '' },
  })

  // Fetch options and reset form when dialog opens
  useEffect(() => {
    if (open) {
      fetchUsers().then((r: any) => setUsers(r || [])).catch(() => setUsers([]))
      fetchTestCases({ page_size: 200 }).then((r: any) => setCases(r?.items || [])).catch(() => setCases([]))

      if (editing) {
        form.reset({
          title: editing.title ?? '',
          description: editing.description ?? '',
          severity: editing.severity ?? 'P2',
          status: editing.status,
          assignee_id: editing.assignee_id ?? null,
          case_id: editing.case_id ?? null,
          external_id: editing.external_id ?? '',
          external_url: editing.external_url ?? '',
        })
      } else {
        form.reset({ title: '', description: '', severity: 'P2', status: undefined, assignee_id: null, case_id: null, external_id: '', external_url: '' })
      }
    }
  }, [open, editing, form])

  const doSave = async (vals: DefectFormValues) => {
    setSaving(true)
    try {
      if (editing?.id) {
        await updateDefect(editing.id, vals)
        toast.success('缺陷已更新')
      } else {
        await createDefect(vals)
        toast.success('缺陷已创建')
      }
      onSaved()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    onClose()
    form.reset()
  }

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) handleClose() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing?.id ? '编辑缺陷' : '新建缺陷'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(doSave)} className="flex flex-col gap-4">
          {/* Title */}
          <div data-invalid={!!form.formState.errors.title} aria-invalid={!!form.formState.errors.title}>
            <label htmlFor="defect-title" className="text-sm font-medium mb-1 block">缺陷标题</label>
            <Input id="defect-title" placeholder="缺陷标题" {...form.register('title')} aria-describedby={form.formState.errors.title ? 'defect-title-error' : undefined} />
            {form.formState.errors.title && (
              <p id="defect-title-error" className="text-xs text-destructive mt-0.5">{form.formState.errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label htmlFor="defect-description" className="text-sm font-medium mb-1 block">详细描述</label>
            <Textarea id="defect-description" rows={3} placeholder="缺陷描述" {...form.register('description')} />
          </div>

          {/* Severity + Status */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="defect-severity" className="text-sm font-medium mb-1 block">严重程度</label>
              <Select value={form.watch('severity')} onValueChange={(v) => form.setValue('severity', v)}>
                <SelectTrigger id="defect-severity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(SEVERITY_MAP).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              {editing?.id ? (
                <>
                  <label htmlFor="defect-status" className="text-sm font-medium mb-1 block">状态</label>
                  <Select value={form.watch('status') ?? ''} onValueChange={(v) => form.setValue('status', v || undefined)}>
                    <SelectTrigger id="defect-status">
                      <SelectValue placeholder="选择状态" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(STATUS_MAP).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </>
              ) : null}
            </div>
          </div>

          {/* Assignee + Case */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="defect-assignee" className="text-sm font-medium mb-1 block">处理人</label>
              <Select
                value={form.watch('assignee_id')?.toString() ?? '__none__'}
                onValueChange={(v) => form.setValue('assignee_id', v === '__none__' ? null : Number(v))}
              >
                <SelectTrigger id="defect-assignee">
                  <SelectValue placeholder="选择处理人" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">未指定</SelectItem>
                  {users.map((u: any) => (
                    <SelectItem key={u.id} value={String(u.id)}>{u.nickname || u.username}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label htmlFor="defect-case" className="text-sm font-medium mb-1 block">关联用例</label>
              <Select
                value={form.watch('case_id')?.toString() ?? '__none__'}
                onValueChange={(v) => form.setValue('case_id', v === '__none__' ? null : Number(v))}
              >
                <SelectTrigger id="defect-case">
                  <SelectValue placeholder="关联用例" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">未关联</SelectItem>
                  {cases.map((c: any) => (
                    <SelectItem key={c.id} value={String(c.id)}>[{c.case_id}] {c.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* External ID + URL */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="defect-external-id" className="text-sm font-medium mb-1 block">外部ID</label>
              <Input id="defect-external-id" placeholder="禅道/Jira 编号" {...form.register('external_id')} />
            </div>
            <div>
              <label htmlFor="defect-external-url" className="text-sm font-medium mb-1 block">外部链接</label>
              <Input id="defect-external-url" placeholder="https://..." {...form.register('external_url')} />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              取消
            </Button>
            <Button type="submit" disabled={saving}>
              {saving && <Loader2 className="size-4 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
