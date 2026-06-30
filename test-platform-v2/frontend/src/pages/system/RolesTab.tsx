import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { createRole, deleteRole, fetchPermissions, fetchRoles, updateRole } from '@/api/system'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
const roleSchema = z.object({
  code: z.string().min(1, '编码必填'),
  name: z.string().min(1, '名称必填'),
  data_scope: z.string().optional(),
  remark: z.string().optional(),
})

type RoleFormData = z.infer<typeof roleSchema>

export default function RolesTab() {
  const [roles, setRoles] = useState<any[]>([])
  const [permGroups, setPermGroups] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [checkedPerms, setCheckedPerms] = useState<string[]>([])

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
  })
  const watchDataScope = watch('data_scope')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rls, perms] = await Promise.all([fetchRoles(), fetchPermissions()])
      setRoles(rls as any)
      setPermGroups(perms as any)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openEdit = (role?: any) => {
    setEditing(role || null)
    if (role) {
      reset({
        code: role.code,
        name: role.name,
        data_scope: role.data_scope || 'project',
        remark: role.remark || '',
      })
      setCheckedPerms(role.permission_codes || [])
    } else {
      reset({ code: '', name: '', data_scope: 'project', remark: '' })
      setCheckedPerms([])
    }
    setDrawer(true)
  }

  const doSave = async (v: RoleFormData) => {
    setSaving(true)
    try {
      const payload: Record<string, any> = {
        ...v,
        permission_codes: checkedPerms,
      }
      if (editing?.id) {
        await updateRole(editing.id, payload)
        toast.success('已更新')
      } else {
        await createRole(payload)
        toast.success('已创建')
      }
      setDrawer(false)
      setEditing(null)
      load()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await deleteRole(id)
    toast.success('已删除')
    load()
  }

  const togglePerm = (code: string, checked: boolean | 'indeterminate') => {
    if (checked === 'indeterminate') return
    setCheckedPerms((prev) =>
      checked ? [...prev, code] : prev.filter((c) => c !== code)
    )
  }

  // "super" checkbox toggles all
  const isSuperChecked = checkedPerms.includes('*')
  const toggleSuper = (checked: boolean | 'indeterminate') => {
    if (checked === 'indeterminate') return
    if (checked) {
      setCheckedPerms(['*'])
    } else {
      setCheckedPerms([])
    }
  }

  return (
    <div>
      <Button size="sm" onClick={() => openEdit()} className="mb-3" data-icon="inline-start">
        <Plus />
        新建角色
      </Button>

      {/* Table */}
      <div className="rounded-xl border bg-card text-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">编码</TableHead>
              <TableHead>名称</TableHead>
              <TableHead className="w-[80px]">数据范围</TableHead>
              <TableHead className="w-[70px]">权限数</TableHead>
              <TableHead className="w-[140px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  <Loader2 className="inline-block size-4 animate-spin mr-2" />
                  加载中...
                </TableCell>
              </TableRow>
            ) : roles.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              roles.map((r: any) => (
                <TableRow key={r.id}>
                  <TableCell>{r.code}</TableCell>
                  <TableCell>{r.name}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {r.data_scope === 'global' ? '全局' : '本项目'}
                    </Badge>
                  </TableCell>
                  <TableCell>{r.permission_codes?.length || 0}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="outline" onClick={() => openEdit(r)}>编辑</Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button size="sm" variant="destructive">删除</Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>确定删除？</AlertDialogTitle>
                            <AlertDialogDescription>
                              将删除角色「{r.name}」，此操作不可撤销。
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>取消</AlertDialogCancel>
                            <AlertDialogAction variant="destructive" onClick={() => doDelete(r.id)}>
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
        <SheetContent side="right" className="w-[560px] sm:max-w-[560px]">
          <SheetHeader>
            <SheetTitle>{editing?.id ? '编辑角色' : '新建角色'}</SheetTitle>
            <SheetDescription>
              {editing?.id ? '修改角色信息与权限' : '创建一个新的系统角色'}
            </SheetDescription>
          </SheetHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4 py-4 flex-1 overflow-y-auto">
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.code} aria-invalid={!!errors.code}>
              <label className="text-sm font-medium">编码</label>
              <Input
                disabled={!!editing?.id}
                placeholder="角色编码"
                {...register('code')}
                className={cn(errors.code && 'border-destructive')}
              />
              {errors.code && <span className="text-xs text-destructive">{errors.code.message}</span>}
            </div>

            <div className="flex flex-col gap-1.5" data-invalid={!!errors.name} aria-invalid={!!errors.name}>
              <label className="text-sm font-medium">名称</label>
              <Input
                placeholder="角色名称"
                {...register('name')}
                className={cn(errors.name && 'border-destructive')}
              />
              {errors.name && <span className="text-xs text-destructive">{errors.name.message}</span>}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">数据范围</label>
              <Select
                value={watchDataScope || 'project'}
                onValueChange={(v) => setValue('data_scope', v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择数据范围" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="global">全局</SelectItem>
                  <SelectItem value="project">本项目</SelectItem>
                  <SelectItem value="self">仅自己</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">备注</label>
              <Textarea rows={2} placeholder="备注信息" {...register('remark')} />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">权限分配</label>
              <div className="rounded-lg border border-input p-3 max-h-[360px] overflow-y-auto">
                {/* Super perm */}
                <label className="flex items-center gap-2 mb-3 cursor-pointer">
                  <Checkbox
                    checked={isSuperChecked}
                    onCheckedChange={toggleSuper}
                  />
                  <span className="text-sm font-semibold">超级权限 (*)</span>
                </label>

                {/* Permission groups */}
                {permGroups.map((g: any) => (
                  <div key={g.group} className="mb-3">
                    <div className="text-xs text-muted-foreground font-medium mb-1.5">{g.group}</div>
                    <div className="flex flex-wrap gap-2">
                      {g.items.map((p: any) => (
                        <label key={p.code} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <Checkbox
                            checked={checkedPerms.includes(p.code)}
                            onCheckedChange={(checked) => togglePerm(p.code, checked)}
                          />
                          {p.name}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
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
