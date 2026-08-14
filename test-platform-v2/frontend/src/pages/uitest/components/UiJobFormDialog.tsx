import { useState } from 'react'
import type { UseFormReturn } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/ui'
import { Input } from '@/ui'
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
import { Loader2 } from '@/lib/icons'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchScripts } from '@/api/uitest'
import { BROWSER_MAP } from '../uiShared'
import type { Environment, UiJobItem } from '@/types'

export const uiJobFormSchema = z.object({
  name: z.string().min(1, '请输入任务名称'),
  description: z.string().optional().default(''),
  test_spec: z.string().optional().default(''),
  browser: z.string().default('chromium'),
  environment_id: z.number().nullable().default(null),
  case_id: z.number().nullable().default(null),
  cron_expression: z.string().optional().default(''),
  schedule_enabled: z.boolean().optional().default(false),
})

export type UiJobFormValues = z.infer<typeof uiJobFormSchema>

interface UiJobFormDialogProps {
  open: boolean
  onClose: () => void
  form: UseFormReturn<UiJobFormValues>
  editing: UiJobItem | null
  saving: boolean
  environments: Environment[]
  uiCases: any[]
  onSubmit: (vals: UiJobFormValues) => void
}

export default function UiJobFormDialog({
  open,
  onClose,
  form,
  editing,
  saving,
  environments,
  uiCases,
  onSubmit,
}: UiJobFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{editing?.id ? '编辑UI测试任务' : '新建UI测试任务'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div data-invalid={!!form.formState.errors.name} aria-invalid={!!form.formState.errors.name}>
            <label className="text-sm font-medium mb-1 block">任务名称</label>
            <Input placeholder="如：首页推荐冒烟测试" {...form.register('name')} />
            {form.formState.errors.name && (
              <p className="text-xs text-destructive mt-0.5">{form.formState.errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">描述</label>
            <Textarea rows={3} placeholder="测试说明" {...form.register('description')} />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">测试脚本</label>
            <ScriptSelector
              value={form.watch('test_spec') || ''}
              onChange={(v) => form.setValue('test_spec', v)}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">定时 Cron（B112-3）</label>
            <Input
              placeholder="如 0 2 * * *（每日 02:00，空=不定时）"
              value={form.watch('cron_expression') || ''}
              onChange={(e) => form.setValue('cron_expression', e.target.value)}
            />
            <label className="flex items-center gap-2 mt-2 text-sm">
              <input
                type="checkbox"
                checked={form.watch('schedule_enabled') || false}
                onChange={(e) => form.setValue('schedule_enabled', e.target.checked)}
              />
              启用定时回归
            </label>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">浏览器</label>
            <Select value={form.watch('browser')} onValueChange={(v) => form.setValue('browser', v)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.keys(BROWSER_MAP).map((k) => (
                  <SelectItem key={k} value={k}>{k}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">关联用例</label>
            <Select
              value={form.watch('case_id') == null ? '__none__' : String(form.watch('case_id'))}
              onValueChange={(v) => form.setValue('case_id', v === '__none__' ? null : Number(v))}
            >
              <SelectTrigger aria-label="关联用例">
                <SelectValue placeholder="选择 UI 用例" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">不关联</SelectItem>
                {uiCases.map((c: any) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">运行环境</label>
            <Select
              value={form.watch('environment_id') == null ? '__none__' : String(form.watch('environment_id'))}
              onValueChange={(v) => form.setValue('environment_id', v === '__none__' ? null : Number(v))}
            >
              <SelectTrigger aria-label="运行环境">
                <SelectValue placeholder="选择运行环境" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">不绑定环境</SelectItem>
                {environments.map((env) => (
                  <SelectItem key={env.id} value={String(env.id)}>
                    {env.name}（{env.base_url || '未配置 Base URL'}）
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              执行时会把所选环境的 Base URL 注入 Playwright。
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="secondary" onClick={onClose}>
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

// ── Script Selector ──

function ScriptSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [scripts, setScripts] = useState<string[]>([])
  const [custom, setCustom] = useState(false)

  useAbortableEffect((signal) => {
    fetchScripts(signal)
      .then((rows) => { if (!signal.aborted) setScripts(rows) })
      .catch(() => { if (!signal.aborted) setScripts([]) })
  }, [])

  if (scripts.length === 0 || custom) {
    return (
      <div className="flex gap-2">
        <Input placeholder="tests/login.spec.js" value={value} onChange={(e) => onChange(e.target.value)} />
        {scripts.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => setCustom(false)}>选择</Button>
        )}
      </div>
    )
  }

  return (
    <div className="flex gap-2">
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger><SelectValue placeholder="选择测试脚本" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="">(空)</SelectItem>
          {scripts.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
        </SelectContent>
      </Select>
      <Button variant="ghost" size="sm" onClick={() => setCustom(true)}>自定义</Button>
    </div>
  )
}
