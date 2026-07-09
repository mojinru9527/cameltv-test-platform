import { useEffect, useState } from 'react'
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
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import PageHeader from '@/components/PageHeader'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
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

export default function ProjectPage() {
  useDocumentTitle('项目管理')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, error, refetch } = useApi<any>(
    () => api.get('/projects/all', { params: { page, page_size: 20 } }),
    { deps: [page], initialData: { total: 0, items: [] as ProjectDetail[], page: 1, page_size: 20 } },
  )

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

  // ── DataTable column definitions ──
  const projectColumns: DataTableColumn<ProjectDetail>[] = [
    { key: 'code', header: '编码', headerClassName: 'w-[120px]', className: 'max-w-[120px] truncate', render: (r) => r.code },
    { key: 'name', header: '名称', className: 'truncate', render: (r) => r.name },
    { key: 'description', header: '描述', className: 'truncate', render: (r) => r.description || '-' },
    { key: 'owner_name', header: '负责人', headerClassName: 'w-[100px]', render: (r) => (r as any).owner_name || '-' },
    { key: 'status', header: '状态', headerClassName: 'w-[80px]', render: (r) => (
      <Badge variant={r.status === 1 ? 'default' : 'secondary'}>
        {r.status === 1 ? '启用' : '禁用'}
      </Badge>
    )},
    { key: 'actions', header: '操作', headerClassName: 'w-[200px]', render: (r) => (
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
    )},
  ]

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
      refetch()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await api.delete(`/projects/${id}`)
    toast.success('已删除')
    refetch()
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
    } catch {
      toast.error('获取成员数据失败')
    }
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
    } catch {
      toast.error('添加成员失败')
    }
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
      <PageHeader title="项目管理">
        <Button variant="outline" size="sm" onClick={refetch} data-icon="inline-start">
          <RotateCcw />
          刷新
        </Button>
        {hasPerm('project:create') && (
          <Button size="sm" onClick={openCreate} data-icon="inline-start">
            <Plus />
            新建项目
          </Button>
        )}
      </PageHeader>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data?.items}
        onRetry={refetch}
        emptyTitle="暂无项目"
        emptyDescription="点击「新建项目」开始创建"
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
        <DataTable
          columns={projectColumns}
          data={data?.items ?? []}
          rowKey={(r) => r.id}
          loading={isLoading}
          loadingRows={4}
          pagination={{
            page: data?.page ?? 1,
            totalPages: Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20))),
            total: data?.total ?? 0,
            onChange: (p) => setPage(p),
          }}
        />
        )}
      </AsyncState>

      {/* Quality Gate Config */}
      <QualityGateCard />

      {/* Create/Edit Dialog */}
      <Dialog open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null) } }}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>{editing?.id ? '编辑项目' : '新建项目'}</DialogTitle>
            <DialogDescription>
              {editing?.id ? '修改项目信息' : '创建一个新的测试项目'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.code} aria-invalid={!!errors.code}>
              <label htmlFor="project-code" className="text-sm font-medium">项目编码</label>
              <Input
                id="project-code"
                placeholder="如：cameltv"
                disabled={!!editing?.id}
                {...register('code')}
                className={cn(errors.code && 'border-destructive')}
                aria-describedby={errors.code ? 'project-code-error' : undefined}
              />
              {errors.code && <span id="project-code-error" className="text-xs text-destructive">{errors.code.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.name} aria-invalid={!!errors.name}>
              <label htmlFor="project-name" className="text-sm font-medium">项目名称</label>
              <Input
                id="project-name"
                placeholder="项目显示名"
                {...register('name')}
                className={cn(errors.name && 'border-destructive')}
                aria-describedby={errors.name ? 'project-name-error' : undefined}
              />
              {errors.name && <span id="project-name-error" className="text-xs text-destructive">{errors.name.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="project-description" className="text-sm font-medium">描述</label>
              <Textarea id="project-description" placeholder="项目说明" rows={3} {...register('description')} />
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
                      <SelectTrigger id="member-user" className="w-[180px]" aria-label="选择用户">
                        <SelectValue placeholder="选择用户" />
                      </SelectTrigger>
                      <SelectContent>
                        {users.map((u: any) => (
                          <SelectItem key={u.id} value={String(u.id)}>{u.nickname || u.username}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {memberErrors.user_id && <span id="member-user-error" className="text-xs text-destructive">{memberErrors.user_id.message}</span>}
                  </div>
                  <div className="flex flex-col gap-1.5" data-invalid={!!memberErrors.role_id} aria-invalid={!!memberErrors.role_id}>
                    <Select
                      value={memberRoleId ? String(memberRoleId) : undefined}
                      onValueChange={(v) => setMemberValue('role_id', Number(v), { shouldValidate: true })}
                    >
                      <SelectTrigger id="member-role" className="w-[180px]" aria-label="选择角色">
                        <SelectValue placeholder="选择角色" />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map((r: any) => (
                          <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {memberErrors.role_id && <span id="member-role-error" className="text-xs text-destructive">{memberErrors.role_id.message}</span>}
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

// ── Quality Gate Config ──

function QualityGateCard() {
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState<any>(null)
  const [form, setForm] = useState({ pass_rate_threshold: 80, p0_max: 0, p1_max: 5, enabled: true })

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const r: any = await api.get('/projects/current')
      const projectId = r.id
      if (!projectId) return
      const g: any = await api.get(`/projects/${projectId}/quality-gate`)
      if (g) {
        setConfig(g)
        setForm({ pass_rate_threshold: g.pass_rate_threshold, p0_max: g.p0_max, p1_max: g.p1_max, enabled: g.enabled })
      }
    } catch { /* no gate config yet */ }
  }

  const saveConfig = async () => {
    setLoading(true)
    try {
      const r: any = await api.get('/projects/current')
      const projectId = r.id
      const result: any = await api.put(`/projects/${projectId}/quality-gate`, form)
      setConfig(result)
      toast.success('门禁配置已保存')
    } catch {
      toast.error('保存失败')
    } finally { setLoading(false) }
  }

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">质量门禁配置</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-4 items-end">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="gate-pass-rate" className="text-sm font-medium">通过率阈值 (%)</label>
            <Input
              id="gate-pass-rate"
              type="number"
              min={0}
              max={100}
              value={form.pass_rate_threshold}
              onChange={(e) => setForm((f) => ({ ...f, pass_rate_threshold: parseInt(e.target.value) || 0 }))}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="gate-p0-max" className="text-sm font-medium">P0 缺陷上限</label>
            <Input
              id="gate-p0-max"
              type="number"
              min={0}
              value={form.p0_max}
              onChange={(e) => setForm((f) => ({ ...f, p0_max: parseInt(e.target.value) || 0 }))}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="gate-p1-max" className="text-sm font-medium">P1 缺陷上限</label>
            <Input
              id="gate-p1-max"
              type="number"
              min={0}
              value={form.p1_max}
              onChange={(e) => setForm((f) => ({ ...f, p1_max: parseInt(e.target.value) || 0 }))}
            />
          </div>
          <div className="flex items-center gap-4">
            <label htmlFor="gate-enabled" className="flex items-center gap-2 cursor-pointer">
              <input
                id="gate-enabled"
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
                className="size-4"
              />
              <span className="text-sm">启用门禁</span>
            </label>
            <Button size="sm" onClick={saveConfig} disabled={loading}>
              {loading ? '保存中...' : '保存'}
            </Button>
          </div>
        </div>
        {config?.is_default !== undefined && (
          <p className="text-xs text-muted-foreground mt-2">
            {config.is_default ? '当前使用默认配置' : '已自定义配置'}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
