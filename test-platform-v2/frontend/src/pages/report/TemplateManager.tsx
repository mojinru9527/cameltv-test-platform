import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Button, Badge, Input } from '@/ui'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  createTemplate,
  deleteTemplate,
  updateTemplate,
  type ReportTemplate,
} from '@/api/reportTemplate'
import { Plus, Edit, Trash2, FileText } from '@/lib/icons'

const templateSchema = z.object({
  name: z.string().min(1, '名称必填'),
  description: z.string().optional(),
  is_default: z.boolean(),
})

type TemplateFormData = z.infer<typeof templateSchema>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  templates: ReportTemplate[]
  onChanged: () => void
}

export default function TemplateManager({ open, onOpenChange, templates, onChanged }: Props) {
  const [editing, setEditing] = useState<ReportTemplate | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<ReportTemplate | null>(null)
  const [sectionEnabled, setSectionEnabled] = useState<Record<string, boolean>>({})
  const { register, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<TemplateFormData>({
    resolver: zodResolver(templateSchema),
    defaultValues: { name: '', description: '', is_default: false },
  })

  function openEdit(t: ReportTemplate) {
    setEditing(t)
    reset({ name: t.name, description: t.description ?? '', is_default: t.is_default })
    setSectionEnabled(
      Object.fromEntries((t.sections ?? []).map((s) => [s.key, Boolean(s.enabled)])),
    )
  }

  async function onSubmit(data: TemplateFormData) {
    setSaving(true)
    try {
      if (editing) {
        const sections = (editing.sections ?? []).map((s) => ({
          ...s,
          enabled: sectionEnabled[s.key] ?? s.enabled,
        }))
        await updateTemplate(editing.id, { ...data, sections })
        toast.success('模板已更新')
      } else {
        await createTemplate(data)
        toast.success('模板已创建')
      }
      onChanged()
      setEditing(null)
    } catch (e: any) {
      toast.error(e?.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  async function onDelete() {
    if (!deleting) return
    try {
      await deleteTemplate(deleting.id)
      toast.success('模板已删除')
      onChanged()
    } catch (e: any) {
      toast.error(e?.message || '删除失败')
    } finally {
      setDeleting(null)
    }
  }

  async function onSetDefault(t: ReportTemplate) {
    try {
      await updateTemplate(t.id, { is_default: true })
      toast.success(`「${t.name}」已设为默认`)
      onChanged()
    } catch (e: any) {
      toast.error(e?.message || '设置失败')
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>报告模板管理</DialogTitle>
            <DialogDescription>新建、编辑或删除报告模板；默认模板用于报告生成兜底。</DialogDescription>
          </DialogHeader>

          <div className="max-h-72 space-y-2 overflow-auto rounded-md border p-2">
            {templates.length === 0 && (
              <p className="px-2 py-4 text-center text-sm text-muted-foreground">暂无模板</p>
            )}
            {templates.map((t) => (
              <div key={t.id} className="flex items-center gap-2 rounded border px-3 py-2">
                <FileText className="size-4 shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {t.name} {t.is_default && <Badge>默认</Badge>}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {t.description || '（无描述）'} · {t.sections?.length ?? 0} 个章节
                  </p>
                </div>
                {!t.is_default && (
                  <Button variant="ghost" size="sm" onClick={() => onSetDefault(t)}>
                    设为默认
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => openEdit(t)}>
                  <Edit className="size-3.5" data-icon="inline-start" />
                  编辑
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDeleting(t)}>
                  <Trash2 className="size-3.5" data-icon="inline-start" />
                  删除
                </Button>
              </div>
            ))}
          </div>

          <div className="rounded-md border p-3">
            <p className="mb-2 text-sm font-medium">{editing ? '编辑模板' : '新建模板'}</p>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <Input placeholder="模板名称" {...register('name')} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
              <Input placeholder="描述（可选）" {...register('description')} />
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={watch('is_default')}
                  onCheckedChange={(v) => setValue('is_default', Boolean(v))}
                />
                设为默认模板
              </label>
              {editing && (editing.sections?.length ?? 0) > 0 && (
                <div className="space-y-1 rounded border p-2">
                  <p className="text-xs text-muted-foreground">章节启用</p>
                  {editing.sections.map((s) => (
                    <label key={s.key} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={sectionEnabled[s.key] ?? Boolean(s.enabled)}
                        onCheckedChange={(v) =>
                          setSectionEnabled((prev) => ({ ...prev, [s.key]: Boolean(v) }))
                        }
                      />
                      {s.label}
                    </label>
                  ))}
                </div>
              )}
              <DialogFooter>
                {editing && (
                  <Button type="button" variant="ghost" onClick={() => { setEditing(null); reset({ name: '', description: '', is_default: false }) }}>
                    取消编辑
                  </Button>
                )}
                <Button type="submit" disabled={saving}>
                  <Plus className="size-4" />
                  {saving ? '保存中...' : editing ? '保存' : '创建'}
                </Button>
              </DialogFooter>
            </form>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting !== null} onOpenChange={(o) => { if (!o) setDeleting(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除模板</AlertDialogTitle>
            <AlertDialogDescription>确定删除「{deleting?.name}」？</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )

}
