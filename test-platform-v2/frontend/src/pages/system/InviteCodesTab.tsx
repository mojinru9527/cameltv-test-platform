import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  createInviteCode,
  disableInviteCode,
  fetchInviteCodes,
  type InviteCode,
} from '@/api/system'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Badge } from '@/ui'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Plus, Loader2, Copy, KeyRound } from '@/lib/icons'

const inviteSchema = z.object({
  usage_limit: z.coerce.number().int().min(1, '至少 1 次').max(1000, '上限 1000 次'),
  expires_at: z.string().optional(),
})

type InviteFormData = z.infer<typeof inviteSchema>

function inviteStatus(code: InviteCode): { label: string; tone: 'success' | 'neutral' } {
  if (code.status !== 1) return { label: '已停用', tone: 'neutral' }
  if (code.used_count >= code.usage_limit) return { label: '已用尽', tone: 'neutral' }
  return { label: '启用', tone: 'success' }
}

export default function InviteCodesTab() {
  useDocumentTitle('邀请码管理')
  const { data, isLoading, isError, error, refetch } = useApi<InviteCode[]>(
    () => fetchInviteCodes(),
    { deps: [], initialData: [] },
  )

  const [createOpen, setCreateOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [createdCode, setCreatedCode] = useState<InviteCode | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { usage_limit: 1, expires_at: '' },
  })

  const doCreate = async (vals: InviteFormData) => {
    setSaving(true)
    try {
      const expires_at = vals.expires_at ? new Date(vals.expires_at).toISOString() : null
      const created = await createInviteCode({ usage_limit: vals.usage_limit, expires_at })
      setCreatedCode(created)
      setCreateOpen(false)
      reset()
      refetch()
    } catch {
      // 错误已由拦截器提示
    } finally {
      setSaving(false)
    }
  }

  const doDisable = async (id: number) => {
    await disableInviteCode(id)
    toast.success('邀请码已停用')
    refetch()
  }

  const copyCode = async () => {
    if (!createdCode) return
    try {
      await navigator.clipboard.writeText(createdCode.code)
      toast.success('邀请码已复制')
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  const columns: DataTableColumn<InviteCode>[] = [
    {
      key: 'code',
      header: '邀请码',
      className: 'w-[140px]',
      render: (r) => (
        <span className="font-mono text-xs" title={r.code}>
          ****{r.code.slice(-4)}
        </span>
      ),
    },
    {
      key: 'usage',
      header: '已用/上限',
      className: 'w-[100px]',
      render: (r) => `${r.used_count} / ${r.usage_limit}`,
    },
    {
      key: 'expires_at',
      header: '过期时间',
      className: 'w-[160px]',
      render: (r) => (r.expires_at ? new Date(r.expires_at).toLocaleString() : '永不过期'),
    },
    {
      key: 'created_by_name',
      header: '创建人',
      className: 'w-[120px]',
      render: (r) => r.created_by_name || '-',
    },
    {
      key: 'status',
      header: '状态',
      className: 'w-[90px]',
      render: (r) => {
        const s = inviteStatus(r)
        return <Badge tone={s.tone}>{s.label}</Badge>
      },
    },
    {
      key: 'actions',
      header: '操作',
      className: 'w-[100px]',
      render: (r) => (
        <div className="flex items-center gap-2">
          {r.status === 1 && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="danger">
                  停用
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>确定停用？</AlertDialogTitle>
                  <AlertDialogDescription>
                    停用后该邀请码无法再注册新用户，已注册用户不受影响。
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction variant="destructive" onClick={() => void doDisable(r.id)}>
                    停用
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      ),
    },
  ]

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          邀请码用于新用户注册；生成后请通过安全渠道发给受邀用户。
        </p>
        <Button size="sm" onClick={() => setCreateOpen(true)} data-icon="inline-start">
          <Plus />
          生成邀请码
        </Button>
      </div>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        emptyTitle="暂无邀请码"
        emptyDescription="点击「生成邀请码」创建第一个注册入口"
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
          <DataTable columns={columns} data={data ?? []} rowKey={(r) => r.id} loading={isLoading} loadingRows={4} />
        )}
      </AsyncState>

      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) { setCreateOpen(false); reset() } }}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>生成邀请码</DialogTitle>
            <DialogDescription>设置可注册次数与有效期（可选）</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(doCreate)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="invite-usage-limit" className="text-sm font-medium">可注册次数</label>
              <Input
                id="invite-usage-limit"
                type="number"
                min={1}
                max={1000}
                {...register('usage_limit')}
                aria-describedby={errors.usage_limit ? 'usage-limit-error' : undefined}
              />
              {errors.usage_limit && (
                <span id="usage-limit-error" className="text-xs text-destructive">{errors.usage_limit.message}</span>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="invite-expires-at" className="text-sm font-medium">过期时间（可选）</label>
              <Input
                id="invite-expires-at"
                type="datetime-local"
                {...register('expires_at')}
              />
              <p className="text-xs text-muted-foreground">留空表示永不过期</p>
            </div>
          </form>
          <DialogFooter>
            <Button variant="secondary" onClick={() => { setCreateOpen(false); reset() }}>
              取消
            </Button>
            <Button disabled={saving} onClick={() => handleSubmit(doCreate)()} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              生成
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={createdCode !== null} onOpenChange={(open) => { if (!open) setCreatedCode(null) }}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>邀请码已生成</DialogTitle>
            <DialogDescription>请复制后通过安全渠道发送给受邀用户，此页面关闭后不再显示完整邀请码</DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded-lg border bg-muted p-3">
            <KeyRound className="size-4 text-muted-foreground" />
            <code className="flex-1 font-mono text-lg tracking-[0.2em]">{createdCode?.code}</code>
            <Button size="sm" variant="secondary" onClick={() => void copyCode()} data-icon="inline-start">
              <Copy />
              复制
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={() => setCreatedCode(null)}>完成</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
