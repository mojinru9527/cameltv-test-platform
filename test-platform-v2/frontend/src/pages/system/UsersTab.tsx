import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { createUser, deleteUser, fetchRoles, fetchUsers, updateUser } from '@/api/system'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Checkbox } from '@/components/ui/checkbox'
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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { cn } from '@/lib/utils'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import { Plus, Loader2 } from '@/lib/icons'

// ── Zod schema ──
const userSchema = z.object({
  username: z.string().min(1, '用户名必填'),
  password: z.string().optional(),
  nickname: z.string().optional(),
  email: z.string().optional(),
  status: z.boolean(),
})

type UserFormData = z.infer<typeof userSchema>

export default function UsersTab() {
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [selectedRoleCodes, setSelectedRoleCodes] = useState<string[]>([])

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    control,
  } = useForm<UserFormData>({
    resolver: zodResolver(userSchema),
    defaultValues: { status: true, username: '', password: '', nickname: '', email: '' },
  })

  const {
    data: usersAndRoles,
    isLoading,
    isError,
    error,
    refetch,
  } = useApi<any>(
    () => Promise.all([fetchUsers(), fetchRoles()]),
    { showErrorToast: true },
  )

  const users: any[] = (usersAndRoles?.[0] as any) ?? []
  const roles: any[] = (usersAndRoles?.[1] as any) ?? []

  const doSave = async (v: UserFormData) => {
    setSaving(true)
    try {
      const payload: Record<string, any> = {
        ...v,
        status: v.status ? 1 : 0,
        role_codes: selectedRoleCodes,
      }
      if (editing?.id && !payload.password) {
        delete payload.password
      }
      if (editing?.id) {
        await updateUser(editing.id, payload)
        toast.success('已更新')
      } else {
        await createUser(payload)
        toast.success('已创建')
      }
      setDrawer(false)
      setEditing(null)
      refetch()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await deleteUser(id)
    toast.success('已删除')
    refetch()
  }

  const openEdit = (u?: any) => {
    setEditing(u || null)
    if (u) {
      reset({
        username: u.username,
        password: '',
        nickname: u.nickname || '',
        email: u.email || '',
        status: u.status === 1,
      })
      setSelectedRoleCodes(u.role_codes || [])
    } else {
      reset({ username: '', password: '', nickname: '', email: '', status: true })
      setSelectedRoleCodes([])
    }
    setDrawer(true)
  }

  const toggleRoleCode = (code: string, checked: boolean | 'indeterminate') => {
    if (checked === 'indeterminate') return
    setSelectedRoleCodes((prev) =>
      checked ? [...prev, code] : prev.filter((c) => c !== code)
    )
  }

  // ── DataTable column definitions ──
  const userColumns: DataTableColumn<any>[] = [
    { key: 'id', header: 'ID', headerClassName: 'w-[50px]', render: (u) => u.id },
    { key: 'username', header: '用户名', render: (u) => u.username },
    { key: 'nickname', header: '昵称', render: (u) => u.nickname || '-' },
    { key: 'email', header: '邮箱', render: (u) => u.email || '-' },
    { key: 'status', header: '状态', headerClassName: 'w-[60px]', render: (u) => (
      <Badge variant={u.status ? 'default' : 'destructive'}>
        {u.status ? '启用' : '禁用'}
      </Badge>
    )},
    { key: 'roles', header: '角色', render: (u) => (
      <div className="flex flex-wrap gap-1">
        {u.role_codes?.map((c: string) => (
          <Badge key={c} variant="secondary">{c}</Badge>
        )) || '-'}
      </div>
    )},
    { key: 'actions', header: '操作', headerClassName: 'w-[140px]', render: (u) => (
      <div className="flex items-center gap-2">
        <Button size="sm" variant="outline" onClick={() => openEdit(u)}>编辑</Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="destructive">删除</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确定删除？</AlertDialogTitle>
              <AlertDialogDescription>
                将删除用户「{u.username}」，此操作不可撤销。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction variant="destructive" onClick={() => doDelete(u.id)}>
                删除
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    )},
  ]

  return (
    <div>
      <Button size="sm" onClick={() => openEdit()} className="mb-3" data-icon="inline-start">
        <Plus />
        新建用户
      </Button>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={usersAndRoles?.[0]}
        onRetry={refetch}
        emptyTitle="暂无用户"
        emptyDescription="点击「新建用户」添加系统用户"
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
        <DataTable
          columns={userColumns}
          data={users}
          rowKey={(u) => u.id}
          loading={isLoading}
          loadingRows={4}
        />
        )}
      </AsyncState>

      {/* Create/Edit Dialog */}
      <Dialog open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null) } }}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>{editing?.id ? '编辑用户' : '新建用户'}</DialogTitle>
            <DialogDescription>
              {editing?.id ? '修改用户信息' : '创建一个新的系统用户'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.username} aria-invalid={!!errors.username}>
              <label htmlFor="user-username" className="text-sm font-medium">用户名</label>
              <Input
                id="user-username"
                disabled={!!editing?.id}
                placeholder="用户名"
                {...register('username')}
                className={cn(errors.username && 'border-destructive')}
                aria-describedby={errors.username ? 'user-username-error' : undefined}
              />
              {errors.username && <span id="user-username-error" className="text-xs text-destructive">{errors.username.message}</span>}
            </div>

            <div className="flex flex-col gap-1.5" data-invalid={!!errors.password} aria-invalid={!!errors.password}>
              <label htmlFor="user-password" className="text-sm font-medium">
                {editing?.id ? '新密码（留空不修改）' : '密码'}
              </label>
              <Input
                id="user-password"
                type="password"
                placeholder={editing?.id ? '留空则不改密码' : ''}
                {...register('password')}
                className={cn(errors.password && 'border-destructive')}
                aria-describedby={errors.password ? 'user-password-error' : undefined}
              />
              {errors.password && <span id="user-password-error" className="text-xs text-destructive">{errors.password.message}</span>}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="user-nickname" className="text-sm font-medium">昵称</label>
              <Input id="user-nickname" placeholder="昵称" {...register('nickname')} />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="user-email" className="text-sm font-medium">邮箱</label>
              <Input id="user-email" placeholder="邮箱" type="email" {...register('email')} />
            </div>

            <div className="flex items-center justify-between">
              <label htmlFor="user-status" className="text-sm font-medium">启用</label>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="user-status"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">角色</label>
              <div className="rounded-lg border border-input p-3 max-h-[200px] overflow-y-auto flex flex-col gap-1">
                {roles.length === 0 ? (
                  <span className="text-xs text-muted-foreground">暂无角色</span>
                ) : (
                  roles.map((r: any) => (
                    <label key={r.code} className="flex items-center gap-2 text-sm cursor-pointer">
                      <Checkbox
                        checked={selectedRoleCodes.includes(r.code)}
                        onCheckedChange={(checked) => toggleRoleCode(r.code, checked)}
                      />
                      {r.name} ({r.code})
                    </label>
                  ))
                )}
              </div>
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setDrawer(false); setEditing(null) }}>
              取消
            </Button>
            <Button disabled={saving} onClick={() => handleSubmit(doSave)()} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
