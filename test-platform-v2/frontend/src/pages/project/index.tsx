import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import api from '@/api/client'
import { fetchRoles, fetchUsers } from '@/api/system'
import { useAuthStore } from '@/stores/auth'
import type { ProjectDetail } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { RotateCcw, Plus, Users, Edit, Trash2, Loader2 } from '@/lib/icons'

// ── Zod schemas ──
const projectSchema = z.object({
  code: z.string().min(1, '项目编码必填'),
  name: z.string().min(1, '项目名称必填'),
  description: z.string().optional(),
})

type ProjectFormData = z.infer<typeof projectSchema>

const memberSchema = z.object({
  user_id: z.coerce.number({ invalid_type_error: '请选择用户' }),
  role_id: z.coerce.number({ invalid_type_error: '请选择角色' }),
})

type MemberFormData = z.infer<typeof memberSchema>

function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number
  pageSize: number
  total: number
  onChange: (p: number) => void
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="flex items-center justify-between pt-4 text-sm text-muted-foreground">
      <span>共 {total} 条</span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          上一页
        </Button>
        <span>
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          下一页
        </Button>
      </div>
    </div>
  )
}

export default function ProjectPage() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [data, setData] = useState({ total: 0, items: [] as ProjectDetail[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)

  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<ProjectDetail | null>(null)
  const [saving, setSaving] = useState(false)

  const [membersOpen, setMembersOpen] = useState(false)
  const [members, setMembers] = useState<any[]>([])
  const [activeProject, setActiveProject] = useState<ProjectDetail | null>(null)
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
  })

  const {
    register: regMember,
    handleSubmit: handleMemberSubmit,
    formState: { errors: memberErrors },
    reset: resetMember,
    setValue: setMemberValue,
    watch: watchMember,
  } = useForm<MemberFormData>({
    resolver: zodResolver(memberSchema),
  })
  const memberUserId = watchMember('user_id')
  const memberRoleId = watchMember('role_id')

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const res: any = await api.get('/projects/all', { params: { page, page_size: 20 } })
      setData(res)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const doSave = async (vals: ProjectFormData) => {
    setSaving(true)
    try {
      if (editing?.id) {
        await api.put(`/projects/${editing.id}`, vals)
        toast.success('项目已更新')
      } else {
        await api.post('/projects', vals)
        toast.success('项目已创建')
      }
      setDrawer(false)
      load()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await api.delete(`/projects/${id}`)
    toast.success('已删除')
    load()
  }

  const openMembers = async (project: ProjectDetail) => {
    setActiveProject(project)
    try {
      const [mRes, uRes, rRes]: any[] = await Promise.all([
        api.get(`/projects/${project.id}/members`),
        fetchUsers(),
        fetchRoles(),
      ])
      setMembers(mRes || [])
      setUsers(Array.isArray(uRes) ? uRes : (uRes as any)?.items || [])
      setRoles(Array.isArray(rRes) ? rRes : (rRes as any)?.items || [])
    } catch { /* ignore */ }
    resetMember({ user_id: undefined as any, role_id: undefined as any })
    setMembersOpen(true)
  }

  const doAddMember = async (vals: MemberFormData) => {
    try {
      await api.post(`/projects/${activeProject?.id}/members`, vals)
      toast.success('成员已添加')
      const mRes: any = await api.get(`/projects/${activeProject?.id}/members`)
      setMembers(mRes || [])
      resetMember({ user_id: undefined as any, role_id: undefined as any })
    } catch { /* ignore */ }
  }

  const doRemoveMember = async (userId: number) => {
    await api.delete(`/projects/${activeProject?.id}/members/${userId}`)
    toast.success('已移除')
    const mRes: any = await api.get(`/projects/${activeProject?.id}/members`)
    setMembers(mRes || [])
  }

  const openCreate = () => {
    reset({ code: '', name: '', description: '' })
    setEditing(null)
    setDrawer(true)
  }

  const openEdit = (r: ProjectDetail) => {
    setEditing(r)
    reset({ code: r.code, name: r.name, description: r.description || '' })
    setDrawer(true)
  }

  return (
    <>
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" onClick={() => load()} data-icon="inline-start">
          <RotateCcw />
          刷新
        </Button>
        {hasPerm('project:create') && (
          <Button size="sm" onClick={openCreate} data-icon="inline-start">
            <Plus />
            新建项目
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border bg-card text-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[120px]">编码</TableHead>
              <TableHead>名称</TableHead>
              <TableHead>描述</TableHead>
              <TableHead className="w-[100px]">负责人</TableHead>
              <TableHead className="w-[80px]">状态</TableHead>
              <TableHead className="w-[200px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="max-w-[120px] truncate">{r.code}</TableCell>
                  <TableCell className="truncate">{r.name}</TableCell>
                  <TableCell className="truncate">{r.description || '-'}</TableCell>
                  <TableCell>{(r as any).owner_name || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={r.status === 1 ? 'default' : 'secondary'}>
                      {r.status === 1 ? '启用' : '禁用'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {hasPerm('project:manage') && (
                        <Button size="sm" variant="outline" onClick={() => openMembers(r)} data-icon="inline-start">
                          <Users />
                          成员
                        </Button>
                      )}
                      {hasPerm('project:update') && (
                        <Button size="sm" variant="outline" onClick={() => openEdit(r)} data-icon="inline-start">
                          <Edit />
                          编辑
                        </Button>
                      )}
                      {hasPerm('project:delete') && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="sm" variant="destructive" data-icon="inline-start">
                              <Trash2 />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>确定删除此项目？</AlertDialogTitle>
                              <AlertDialogDescription>
                                此操作不可撤销。将删除项目「{r.name}」及其关联数据。
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
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Pagination
        page={data.page}
        pageSize={data.page_size}
        total={data.total}
        onChange={(p) => load(p)}
      />

      {/* Create/Edit Sheet */}
      <Sheet open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null) } }}>
        <SheetContent side="right" className="w-[480px] sm:max-w-[480px]">
          <SheetHeader>
            <SheetTitle>{editing?.id ? '编辑项目' : '新建项目'}</SheetTitle>
            <SheetDescription>
              {editing?.id ? '修改项目信息' : '创建一个新的测试项目'}
            </SheetDescription>
          </SheetHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4 py-4 flex-1 overflow-y-auto">
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.code} aria-invalid={!!errors.code}>
              <label className="text-sm font-medium">项目编码</label>
              <Input
                placeholder="如：cameltv"
                disabled={!!editing?.id}
                {...register('code')}
                className={cn(errors.code && 'border-destructive')}
              />
              {errors.code && <span className="text-xs text-destructive">{errors.code.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.name} aria-invalid={!!errors.name}>
              <label className="text-sm font-medium">项目名称</label>
              <Input
                placeholder="项目显示名"
                {...register('name')}
                className={cn(errors.name && 'border-destructive')}
              />
              {errors.name && <span className="text-xs text-destructive">{errors.name.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">描述</label>
              <Textarea placeholder="项目说明" rows={3} {...register('description')} />
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

      {/* Members Sheet */}
      <Sheet open={membersOpen} onOpenChange={(open) => { if (!open) { setMembersOpen(false); setActiveProject(null) } }}>
        <SheetContent side="right" className="w-[600px] sm:max-w-[600px]">
          <SheetHeader>
            <SheetTitle>{activeProject?.name} — 成员管理</SheetTitle>
            <SheetDescription>管理项目成员及其角色</SheetDescription>
          </SheetHeader>

          <div className="py-4 flex-1 overflow-y-auto flex flex-col gap-4">
            {/* Add member card */}
            <Card size="sm">
              <CardHeader>
                <CardTitle>添加成员</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleMemberSubmit(doAddMember)} className="flex items-end gap-2 flex-wrap">
                  <div className="flex flex-col gap-1.5" data-invalid={!!memberErrors.user_id} aria-invalid={!!memberErrors.user_id}>
                    <Select
                      value={memberUserId ? String(memberUserId) : undefined}
                      onValueChange={(v) => setMemberValue('user_id', Number(v), { shouldValidate: true })}
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="选择用户" />
                      </SelectTrigger>
                      <SelectContent>
                        {users.map((u: any) => (
                          <SelectItem key={u.id} value={String(u.id)}>{u.nickname || u.username}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {memberErrors.user_id && <span className="text-xs text-destructive">{memberErrors.user_id.message}</span>}
                  </div>
                  <div className="flex flex-col gap-1.5" data-invalid={!!memberErrors.role_id} aria-invalid={!!memberErrors.role_id}>
                    <Select
                      value={memberRoleId ? String(memberRoleId) : undefined}
                      onValueChange={(v) => setMemberValue('role_id', Number(v), { shouldValidate: true })}
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="选择角色" />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map((r: any) => (
                          <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {memberErrors.role_id && <span className="text-xs text-destructive">{memberErrors.role_id.message}</span>}
                  </div>
                  <Button type="submit" size="sm" data-icon="inline-start">
                    <Plus />
                    添加
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Members table */}
            <div className="rounded-xl border bg-card text-sm">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>用户</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead className="w-[80px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                        暂无成员
                      </TableCell>
                    </TableRow>
                  ) : (
                    members.map((m: any) => (
                      <TableRow key={m.user_id}>
                        <TableCell>{m.username}</TableCell>
                        <TableCell><Badge variant="secondary">{m.role_name}</Badge></TableCell>
                        <TableCell>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button size="sm" variant="destructive" data-icon="inline-start">
                                <Trash2 />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>确定移除？</AlertDialogTitle>
                                <AlertDialogDescription>
                                  将从项目中移除用户「{m.username}」。
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>取消</AlertDialogCancel>
                                <AlertDialogAction variant="destructive" onClick={() => doRemoveMember(m.user_id)}>
                                  移除
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
