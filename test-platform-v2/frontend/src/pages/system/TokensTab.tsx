import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useSearchParams } from 'react-router'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  createToken,
  deleteToken,
  fetchTokens,
  updateToken,
  type ApiTokenItem,
} from '@/api/token'
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
import { formatTokenScopes } from './tokenScopes'
import {
  TOKEN_PURPOSES,
  buildWorkerSetup,
  normalizeTokenPurpose,
  scopesForTokenPurpose,
  type TokenPurpose,
} from './tokenPurposes'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const tokenSchema = z.object({
  name: z.string().min(1, '名称必填'),
  purpose: z.enum(['ci', 'worker']),
})

type TokenFormData = z.infer<typeof tokenSchema>

type TokenRow = ApiTokenItem

interface CreatedToken {
  value: string
  purpose: TokenPurpose
}

export default function TokensTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canManage = hasPerm('token:manage')
  const [searchParams] = useSearchParams()
  const initialPurpose = normalizeTokenPurpose(searchParams.get('purpose'))
  const [drawer, setDrawer] = useState(false)
  const [createdToken, setCreatedToken] = useState<CreatedToken | null>(null)
  const [copied, setCopied] = useState<'token' | 'setup' | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<TokenRow | null>(null)
  const { data, isLoading, isError, error, refetch } = useApi<TokenRow[]>(() => fetchTokens(), [])
  const { control, register, handleSubmit, reset, watch, formState: { errors } } = useForm<TokenFormData>({
    resolver: zodResolver(tokenSchema),
    defaultValues: { name: '', purpose: initialPurpose },
  })
  const selectedPurpose = watch('purpose')

  async function onCreate(data: TokenFormData) {
    setCreating(true)
    try {
      const result = await createToken({
        name: data.name,
        scopes: scopesForTokenPurpose(data.purpose),
      })
      if (!result?.token) throw new Error('创建响应未返回 Token，请重试')
      setCreatedToken({ value: result.token, purpose: data.purpose })
      setCopied(null)
      setDrawer(false)
      reset({ name: '', purpose: initialPurpose })
      refetch()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建 Token 失败')
    } finally {
      setCreating(false)
    }
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

  async function copyText(value: string, target: 'token' | 'setup') {
    try {
      if (!navigator.clipboard) throw new Error('clipboard unavailable')
      await navigator.clipboard.writeText(value)
      setCopied(target)
      toast.success(target === 'token' ? 'Token 已复制' : '启动配置已复制')
    } catch {
      toast.error('复制失败，请手动选择文本复制')
    }
  }

  function openCreate() {
    reset({ name: '', purpose: initialPurpose })
    setDrawer(true)
  }

  function closeCreatedToken() {
    setCreatedToken(null)
    setCopied(null)
  }

  const columns: DataTableColumn<TokenRow>[] = [
    { key: 'name', header: '名称' },
    { key: 'token_prefix', header: '前缀', render: (row) => <code className="text-xs">{row.token_prefix}</code> },
    { key: 'scopes', header: '作用域', render: (row) => <Badge variant="outline">{formatTokenScopes(row.scopes)}</Badge> },
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
          创建、轮换和撤销 API 访问令牌。停用或删除后，调用方将立即失效。
        </p>
        {canManage && (
          <Button onClick={openCreate}>
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
            <DialogDescription>选择用途后只授予所需权限；明文仅展示一次。</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onCreate)} className="space-y-3">
            <div className="space-y-1.5">
              <label htmlFor="token-name" className="text-sm font-medium">Token 名称</label>
              <Input id="token-name" placeholder="例如：Test5 Worker" {...register('name')} />
            </div>
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            <div className="space-y-1.5">
              <label htmlFor="token-purpose" className="text-sm font-medium">Token 用途</label>
              <Controller
                name="purpose"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="token-purpose" aria-label="Token 用途" className="h-9 w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TOKEN_PURPOSES.map((purpose) => (
                        <SelectItem key={purpose.value} value={purpose.value}>
                          {purpose.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              <p className="text-xs text-muted-hc">
                {TOKEN_PURPOSES.find((purpose) => purpose.value === selectedPurpose)?.description}
              </p>
            </div>
            <DialogFooter>
              <Button type="submit" loading={creating}>
                <KeyRound className="size-4" />
                创建
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={createdToken !== null} onOpenChange={(open) => { if (!open) closeCreatedToken() }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token 创建成功</DialogTitle>
            <DialogDescription>请立即复制保存，关闭后无法再次查看。</DialogDescription>
          </DialogHeader>
          <div className="flex flex-wrap items-center gap-2 rounded border bg-muted/40 p-3">
            <code className="min-w-0 flex-1 break-all text-xs">{createdToken?.value}</code>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => createdToken && void copyText(createdToken.value, 'token')}
            >
              {copied === 'token' ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied === 'token' ? '已复制' : '复制 Token'}
            </Button>
          </div>
          {createdToken?.purpose === 'worker' && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Worker 启动配置</h3>
              <pre className="max-h-52 overflow-auto whitespace-pre-wrap break-all rounded border bg-muted/40 p-3 text-xs">
                {buildWorkerSetup(createdToken.value, window.location.origin)}
              </pre>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-muted-hc">
                  轮换时先让新 Token 心跳成功，再停用或删除旧 Token。
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => void copyText(
                    buildWorkerSetup(createdToken.value, window.location.origin),
                    'setup',
                  )}
                >
                  {copied === 'setup' ? <Check className="size-4" /> : <Copy className="size-4" />}
                  {copied === 'setup' ? '已复制' : '复制启动配置'}
                </Button>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="secondary" onClick={closeCreatedToken}>关闭</Button>
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
