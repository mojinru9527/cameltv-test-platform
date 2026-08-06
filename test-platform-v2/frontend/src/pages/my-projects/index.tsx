import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import api from '@/api/client'
import { fetchOrganizations } from '@/api/organization'
import { fetchRoles, fetchUsers } from '@/api/system'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/ui'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import PageHeader from '@/components/PageHeader'
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
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
import { Plus, Loader2, Users, Edit, Trash2, ArrowRight, RotateCcw } from '@/lib/icons'
import type { Organization, Project } from '@/types'

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

export default function MyProjectsPage() {
  useDocumentTitle('我的项目')
  const navigate = useNavigate()
  const { user, setProjects, setCurrentProject, hasPerm } = useAuthStore()
  const canCreate = hasPerm('project:self_create') || hasPerm('project:create') || hasPerm('*')

  const { data, isLoading, isError, error, refetch } = useApi<Project[]>(
    (signal) => api.get<unknown, Project[]>('/projects', { signal }),
    { deps: [], initialData: [] },
  )

  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<Project | null>(null)
  const [saving, setSaving] = useState(false)

  const [membersOpen, setMembersOpen] = useState(false)
  const [members, setMembers] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [organizationId, setOrganizationId] = useState<number | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
  })

  const {
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

  const syncProjectSwitcher = useCallback(async () => {
    const visible: any = await api.get('/projects')
    setProjects(Array.isArray(visible) ? visible : [])
  }, [setProjects])

  const isOwner = (project: Project) => Boolean(user && project.owner_id === user.id)

  const doSave = async (vals: ProjectFormData) => {
    setSaving(true)
    try {
      if (editing?.id) {
        await api.put(`/projects/${editing.id}`, vals)
        toast.success('项目已更新')
      } else {
        await api.post('/projects', {
          ...vals,
          organization_id: organizationId ?? undefined,
        })
        toast.success('项目已创建')
      }
      await syncProjectSwitcher()
      setDrawer(false)
      setEditing(null)
      refetch()
    } finally {
      setSaving(false)
    }
  }

  const doDelete = async (id: number) => {
    await api.delete(`/projects/${id}`)
    await syncProjectSwitcher()
    toast.success('项目已停用')
    refetch()
  }

  const enterProject = (project: Project) => {
    setCurrentProject(project.id)
    navigate('/workbench')
  }

  const openMembers = async (project: Project) => {
    setActiveProject(project)
    resetMember({ user_id: undefined as any, role_id: undefined as any })
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
    setMembersOpen(true)
  }

  const doAddMember = async (vals: MemberFormData) => {
    try {
      await api.post(`/projects/${activeProject?.id}/members`, vals)
      toast.success('已邀请，同事登录后即可看到该项目')
      const mRes: any = await api.get(`/projects/${activeProject?.id}/members`)
      setMembers(mRes || [])
      resetMember({ user_id: undefined as any, role_id: undefined as any })
    } catch {
      toast.error('邀请失败')
    }
  }

  const doRemoveMember = async (userId: number) => {
    await api.delete(`/projects/${activeProject?.id}/members/${userId}`)
    toast.success('已移除')
    const mRes: any = await api.get(`/projects/${activeProject?.id}/members`)
    setMembers(mRes || [])
  }

  const openCreate = async () => {
    reset({ code: '', name: '', description: '' })
    setEditing(null)
    try {
      const orgs = await fetchOrganizations()
      setOrganizations(orgs || [])
      const personal = (orgs || []).find((o) => o.type === 'personal')
      setOrganizationId(personal?.id ?? orgs?.[0]?.id ?? null)
    } catch {
      setOrganizations([])
      setOrganizationId(null)
    }
    setDrawer(true)
  }

  const openEdit = (r: Project) => {
    setEditing(r)
    reset({ code: r.code, name: r.name, description: r.description || '' })
    setDrawer(true)
  }

  const columns: DataTableColumn<Project>[] = [
    {
      key: 'name',
      header: '项目',
      className: 'min-w-[180px]',
      render: (r) => (
        <div className="flex flex-col">
          <span className="font-medium">{r.name}</span>
          <span className="text-xs text-muted-foreground">{r.code}</span>
        </div>
      ),
    },
    {
      key: 'description',
      header: '描述',
      className: 'hidden md:table-cell max-w-[320px] truncate',
      render: (r) => r.description || '-',
    },
    {
      key: 'organization_name',
      header: '所属组织',
      className: 'w-[140px]',
      render: (r) => <span className="text-xs text-muted-foreground">{r.organization_name || '-'}</span>,
    },
    {
      key: 'owner',
      header: '角色',
      className: 'w-[100px]',
      render: (r) => (
        <Badge tone={isOwner(r) ? 'success' : 'neutral'}>
          {isOwner(r) ? '负责人' : '成员'}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: '状态',
      className: 'w-[80px]',
      render: (r) => (
        <Badge tone={r.status === 1 ? 'success' : 'neutral'}>
          {r.status === 1 ? '启用' : '停用'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '操作',
      className: 'w-[220px]',
      render: (r) => (
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => enterProject(r)} data-icon="inline-start">
            <ArrowRight />
            进入
          </Button>
          {isOwner(r) && (
            <>
              <Button size="sm" variant="secondary" onClick={() => openMembers(r)} data-icon="inline-start">
                <Users />
                成员
              </Button>
              <Button size="sm" variant="secondary" onClick={() => openEdit(r)} data-icon="inline-start">
                <Edit />
                编辑
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button size="sm" variant="danger" aria-label={`停用项目 ${r.name}`}>
                    <Trash2 />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>确定停用此项目？</AlertDialogTitle>
                    <AlertDialogDescription>
                      项目「{r.name}」将从项目切换器移除并停止使用；历史数据和审计记录仍会保留。
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction variant="destructive" onClick={() => void doDelete(r.id)}>
                      停用
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          )}
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader title="我的项目">
        <Button variant="secondary" size="sm" onClick={refetch} data-icon="inline-start">
          <RotateCcw />
          刷新
        </Button>
        {canCreate && (
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
        data={data}
        onRetry={refetch}
        emptyTitle="暂无项目"
        emptyDescription={canCreate ? '创建你的第一个项目，开始使用测试平台功能' : '请联系管理员将你加入项目'}
        emptyAction={canCreate ? { label: '新建项目', onClick: openCreate } : undefined}
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
          <DataTable columns={columns} data={data ?? []} rowKey={(r) => r.id} loading={isLoading} loadingRows={4} />
        )}
      </AsyncState>

      <Dialog open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null) } }}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>{editing?.id ? '编辑项目' : '新建项目'}</DialogTitle>
            <DialogDescription>
              {editing?.id ? '修改项目信息' : '创建后你将自动成为项目负责人'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="project-code" className="text-sm font-medium">项目编码</label>
              <Input
                id="project-code"
                placeholder="如：myapp"
                disabled={!!editing?.id}
                {...register('code')}
                className={cn(errors.code && 'border-destructive')}
                aria-describedby={errors.code ? 'project-code-error' : undefined}
              />
              {errors.code && <span id="project-code-error" className="text-xs text-destructive">{errors.code.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
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
            {!editing && (
              <div className="flex flex-col gap-1.5">
                <label htmlFor="project-org" className="text-sm font-medium">所属组织</label>
                <Select
                  value={organizationId !== null ? String(organizationId) : undefined}
                  onValueChange={(v) => setOrganizationId(Number(v))}
                >
                  <SelectTrigger id="project-org" className="w-full" aria-label="选择组织">
                    <SelectValue placeholder="选择组织" />
                  </SelectTrigger>
                  <SelectContent>
                    {organizations.map((o) => (
                      <SelectItem key={o.id} value={String(o.id)}>
                        {o.name}（{o.type === 'personal' ? '个人' : '团队'}）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </form>
          <DialogFooter>
            <Button variant="secondary" onClick={() => { setDrawer(false); setEditing(null) }}>
              取消
            </Button>
            <Button disabled={saving} onClick={() => handleSubmit(doSave)()} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Sheet open={membersOpen} onOpenChange={(open) => { if (!open) { setMembersOpen(false); setActiveProject(null) } }}>
        <SheetContent side="right" className="w-full sm:max-w-[600px]">
          <SheetHeader>
            <SheetTitle>{activeProject?.name} — 邀请同事</SheetTitle>
            <SheetDescription>输入同事的用户名或邮箱邀请加入项目（同事需先注册账号）</SheetDescription>
          </SheetHeader>
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto py-4">
            <form onSubmit={handleMemberSubmit(doAddMember)} className="flex flex-wrap items-end gap-2">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="member-user" className="text-sm font-medium">选择用户</label>
                <Select
                  value={memberUserId ? String(memberUserId) : undefined}
                  onValueChange={(v) => setMemberValue('user_id', Number(v), { shouldValidate: true })}
                >
                  <SelectTrigger id="member-user" className="w-[200px]" aria-label="选择用户">
                    <SelectValue placeholder="选择用户" />
                  </SelectTrigger>
                  <SelectContent>
                    {users.map((u: any) => (
                      <SelectItem key={u.id} value={String(u.id)}>
                        {u.nickname || u.username}（{u.username}）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {memberErrors.user_id && (
                  <span className="text-xs text-destructive">{memberErrors.user_id.message}</span>
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="member-role" className="text-sm font-medium">角色</label>
                <Select
                  value={memberRoleId !== undefined ? String(memberRoleId) : undefined}
                  onValueChange={(v) => setMemberValue('role_id', Number(v), { shouldValidate: true })}
                >
                  <SelectTrigger id="member-role" className="w-[160px]" aria-label="选择角色">
                    <SelectValue placeholder="选择角色" />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map((r: any) => (
                      <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {memberErrors.role_id && (
                  <span className="text-xs text-destructive">{memberErrors.role_id.message}</span>
                )}
              </div>
              <Button type="submit" size="sm" data-icon="inline-start">
                <Plus />
                邀请
              </Button>
            </form>

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
                      <TableCell colSpan={3} className="py-6 text-center text-muted-foreground">
                        暂无成员，邀请你的同事吧
                      </TableCell>
                    </TableRow>
                  ) : (
                    members.map((m: any) => (
                      <TableRow key={m.user_id}>
                        <TableCell>{m.username}</TableCell>
                        <TableCell><Badge tone="neutral">{m.role_name || '默认'}</Badge></TableCell>
                        <TableCell>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button size="sm" variant="danger" aria-label={`从项目中移除用户 ${m.username}`}>
                                <Trash2 />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>确定移除？</AlertDialogTitle>
                                <AlertDialogDescription>将从项目中移除用户「{m.username}」。</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>取消</AlertDialogCancel>
                                <AlertDialogAction variant="destructive" onClick={() => void doRemoveMember(m.user_id)}>
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
