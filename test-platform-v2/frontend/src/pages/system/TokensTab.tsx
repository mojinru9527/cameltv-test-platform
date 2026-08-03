import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { createToken, deleteToken, fetchTokens, updateToken } from '@/api/token'
import { Button, Input, Badge } from '@/ui'
import { Switch } from '@/components/ui/switch'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
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
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import { Plus, KeyRound, Copy, Check } from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'

const tokenSchema = z.object({
  name: z.string().min(1, '名称必填'),
})

type TokenFormData = z.infer<typeof tokenSchema>

interface TokenRow {
  id: number
  name: string
  token_prefix: string
  scopes: string
  enabled: boolean
  last_used_at: string | null
  created_at: string | null
}

export default function TokensTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canManage = hasPerm('token:manage')
  const [drawer, setDrawer] = useState(false)
  const [plainToken, setPlainToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [deleting, setDeleting] = useState<TokenRow | null>(null)
  const { data, isLoading, isError, error, refetch } = useApi<any>(() => fetchTokens(), [])
  const { register, handleSubmit, reset, formState: { errors } } = useForm<TokenFormData>({
    resolver: zodResolver(tokenSchema),
    defaultValues: { name: '' },
  })

  async function onCreate(data: TokenFormData) {
    const d: any = await createToken({ name: data.name })
    setPlainToken(d?.token ?? '')
    setDrawer(false)
    reset()
    refetch()
  }

  async function onToggle(row: TokenRow, enabled: boolean) {
    await updateToken(row.id, { enabled })
    toast.success(`Token「${row.name}」已${enabled ? '启用' : '停用'}`)
    refetch()
  }

  async function onDelete() {
    if (!deleting) return
    await deleteToken(deleting.id)
    toast.success(`Token「${deleting.name}」已删除`)
    setDeleting(null)
    refetch()
  }

  function copyPlain() {
    if (!plainToken) return
    navigator.clipboard?.writeText(plainToken).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const columns: DataTableColumn<TokenRow>[] = [
    { key: 'name', header: '名称' },
    { key: 'token_prefix', header: '前缀', render: (row) => <code className="text-xs">{row.token_prefix}</code> },
    { key: 'scopes', header: '作用域', render: (row) => <Badge variant="outline">{String(row.scopes)}</Badge> },
    {
      key: 'enabled',
      header: '状态',
      render: (row) => (
        <Switch
          checked={row.enabled}
          disabled={!canManage}
          onCheckedChange={(checked) => onToggle(row, checked)}
          aria-label={`切换 ${row.name} 启用状态`}
        />
      ),
    },
    {
      key: 'last_used_at',
      header: '最近使用',
      render: (row) => (row.last_used_at ? new Date(row.last_used_at).toLocaleString() : '—'),
    },
    {
      key: 'created_at',
      header: '创建时间',
      render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '—'),
    },
    {
      key: 'id',
      header: '操作',
      render: (row) => (
        <Button
          variant="ghost"
          size="sm"
          disabled={!canManage}
          onClick={() => setDeleting(row)}
        >
          删除
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          开放 API 访问令牌。明文仅在创建时展示一次，请妥善保存。
        </p>
        {canManage && (
          <Button onClick={() => setDrawer(true)}>
            <Plus className="size-4" />
            新建 Token
          </Button>
        )}
      </div>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        emptyTitle="暂无 API Token"
      >
        {(items) => <DataTable columns={columns} data={items ?? []} rowKey={(row: TokenRow) => row.id} />}
      </AsyncState>

      <Dialog open={drawer} onOpenChange={setDrawer}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建 API Token</DialogTitle>
            <DialogDescription>创建后明文只展示一次。</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onCreate)} className="space-y-3">
            <Input placeholder="Token 名称" {...register('name')} />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            <DialogFooter>
              <Button type="submit">
                <KeyRound className="size-4" />
                创建
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={plainToken !== null} onOpenChange={(open) => { if (!open) setPlainToken(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token 创建成功</DialogTitle>
            <DialogDescription>请立即复制保存，关闭后无法再次查看。</DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded border p-3">
            <code className="flex-1 break-all text-xs">{plainToken}</code>
            <Button variant="secondary" size="sm" onClick={copyPlain}>
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied ? '已复制' : '复制'}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setPlainToken(null)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting !== null} onOpenChange={(open) => { if (!open) setDeleting(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除 Token</AlertDialogTitle>
            <AlertDialogDescription>
              确定删除「{deleting?.name}」？使用该 Token 的调用方将立即失效。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
