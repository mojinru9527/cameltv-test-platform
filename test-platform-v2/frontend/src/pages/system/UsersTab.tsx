import { useCallback, useEffect, useState } from 'react'
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
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
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
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

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [u, r] = await Promise.all([fetchUsers(), fetchRoles()])
      setUsers(u as any)
      setRoles(r as any)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

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
      load()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await deleteUser(id)
    toast.success('已删除')
    load()
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

  return (
    <div>
      <Button size="sm" onClick={() => openEdit()} className="mb-3" data-icon="inline-start">
        <Plus />
        新建用户
      </Button>

      {/* Table */}
      <div className="rounded-xl border bg-card text-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">ID</TableHead>
              <TableHead>用户名</TableHead>
              <TableHead>昵称</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead className="w-[60px]">状态</TableHead>
              <TableHead>角色</TableHead>
              <TableHead className="w-[140px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  <Loader2 className="inline-block size-4 animate-spin mr-2" />
                  加载中...
                </TableCell>
              </TableRow>
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              users.map((u: any) => (
                <TableRow key={u.id}>
                  <TableCell>{u.id}</TableCell>
                  <TableCell>{u.username}</TableCell>
                  <TableCell>{u.nickname || '-'}</TableCell>
                  <TableCell>{u.email || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={u.status ? 'default' : 'destructive'}>
                      {u.status ? '启用' : '禁用'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {u.role_codes?.map((c: string) => (
                        <Badge key={c} variant="secondary">{c}</Badge>
                      )) || '-'}
                    </div>
                  </TableCell>
                  <TableCell>
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
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Sheet */}
      <Sheet open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null) } }}>
        <SheetContent side="right" className="w-[480px] sm:max-w-[480px]">
          <SheetHeader>
            <SheetTitle>{editing?.id ? '编辑用户' : '新建用户'}</SheetTitle>
            <SheetDescription>
              {editing?.id ? '修改用户信息' : '创建一个新的系统用户'}
            </SheetDescription>
          </SheetHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4 py-4 flex-1 overflow-y-auto">
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.username} aria-invalid={!!errors.username}>
              <label className="text-sm font-medium">用户名</label>
              <Input
                disabled={!!editing?.id}
                placeholder="用户名"
                {...register('username')}
                className={cn(errors.username && 'border-destructive')}
              />
              {errors.username && <span className="text-xs text-destructive">{errors.username.message}</span>}
            </div>

            <div className="flex flex-col gap-1.5" data-invalid={!!errors.password} aria-invalid={!!errors.password}>
              <label className="text-sm font-medium">
                {editing?.id ? '新密码（留空不修改）' : '密码'}
              </label>
              <Input
                type="password"
                placeholder={editing?.id ? '留空则不改密码' : ''}
                {...register('password')}
                className={cn(errors.password && 'border-destructive')}
              />
              {errors.password && <span className="text-xs text-destructive">{errors.password.message}</span>}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">昵称</label>
              <Input placeholder="昵称" {...register('nickname')} />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">邮箱</label>
              <Input placeholder="邮箱" type="email" {...register('email')} />
            </div>

            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">启用</label>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Switch
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
          <SheetFooter>
            <Button variant="outline" onClick={() => { setDrawer(false); setEditing(null) }}>
              取消
            </Button>
            <Button disabled={saving} onClick={() => handleSubmit(doSave)()} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              保存
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}
