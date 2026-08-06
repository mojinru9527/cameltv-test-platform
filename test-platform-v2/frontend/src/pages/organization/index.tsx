import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  addOrgMember,
  createOrganization,
  disableOrganization,
  fetchOrgMembers,
  fetchOrgProjects,
  fetchOrganizations,
  removeOrgMember,
  updateOrganization,
  type OrganizationMember,
  type OrgProject,
} from '@/api/organization'
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
import {
  Plus, Loader2, Users, Edit, Trash2, FolderOpen, ArrowRight, RotateCcw,
} from '@/lib/icons'
import type { Organization } from '@/types'

const orgSchema = z.object({
  code: z.string().min(2, '组织编码至少 2 位'),
  name: z.string().min(1, '组织名称必填'),
  description: z.string().optional(),
})

type OrgFormData = z.infer<typeof orgSchema>

const ROLE_LABELS: Record<number, string> = { 1: '负责人', 2: '管理员', 3: '成员' }

function canManage(org: Organization) {
  return org.my_role === 1 || org.my_role === 2
}

export default function OrganizationPage() {
  useDocumentTitle('组织管理')
  const navigate = useNavigate()
  const { setCurrentProject } = useAuthStore()
  const { data, isLoading, isError, error, refetch } = useApi<Organization[]>(
    (signal) => fetchOrganizations(signal),
    { deps: [], initialData: [] },
  )

  const [createOpen, setCreateOpen] = useState(false)
  const [editOrg, setEditOrg] = useState<Organization | null>(null)
  const [saving, setSaving] = useState(false)

  const [membersOrg, setMembersOrg] = useState<Organization | null>(null)
  const [members, setMembers] = useState<OrganizationMember[]>([])
  const [memberUsername, setMemberUsername] = useState('')
  const [memberRole, setMemberRole] = useState('3')
  const [membersLoading, setMembersLoading] = useState(false)

  const [projectsOrg, setProjectsOrg] = useState<Organization | null>(null)
  const [orgProjects, setOrgProjects] = useState<OrgProject[]>([])
  const [projectsLoading, setProjectsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<OrgFormData>({
    resolver: zodResolver(orgSchema),
  })

  const doSave = async (vals: OrgFormData) => {
    setSaving(true)
    try {
      if (editOrg) {
        await updateOrganization(editOrg.id, {
          name: vals.name,
          description: vals.description || '',
        })
        toast.success('组织已更新')
      } else {
        await createOrganization({
          code: vals.code,
          name: vals.name,
          description: vals.description || '',
        })
        toast.success('组织已创建，可在成员管理中邀请同事')
      }
      setCreateOpen(false)
      setEditOrg(null)
      reset()
      refetch()
    } finally {
      setSaving(false)
    }
  }

  const doDisable = async (org: Organization) => {
    await disableOrganization(org.id)
    toast.success(`组织「${org.name}」已停用`)
    refetch()
  }

  const openMembers = async (org: Organization) => {
    setMembersOrg(org)
    setMembers([])
    setMemberUsername('')
    setMemberRole('3')
    setMembersLoading(true)
    try {
      const rows = await fetchOrgMembers(org.id)
      setMembers(rows || [])
    } catch {
      toast.error('获取成员失败')
    } finally {
      setMembersLoading(false)
    }
  }

  const doAddMember = async () => {
    if (!memberUsername.trim()) {
      toast.error('请输入同事的用户名')
      return
    }
    try {
      await addOrgMember(membersOrg!.id, {
        username: memberUsername.trim(),
        role_id: Number(memberRole),
      })
      toast.success('已邀请，同事登录后可见该组织')
      setMemberUsername('')
      const rows = await fetchOrgMembers(membersOrg!.id)
      setMembers(rows || [])
    } catch {
      toast.error('邀请失败')
    }
  }

  const doRemoveMember = async (userId: number) => {
    await removeOrgMember(membersOrg!.id, userId)
    toast.success('已移除')
    const rows = await fetchOrgMembers(membersOrg!.id)
    setMembers(rows || [])
  }

  const openProjects = async (org: Organization) => {
    setProjectsOrg(org)
    setOrgProjects([])
    setProjectsLoading(true)
    try {
      const rows = await fetchOrgProjects(org.id)
      setOrgProjects(rows || [])
    } catch {
      toast.error('获取组织项目失败')
    } finally {
      setProjectsLoading(false)
    }
  }

  const enterProject = (project: OrgProject) => {
    setCurrentProject(project.id)
    navigate('/workbench')
  }

  const openCreate = () => {
    reset({ code: '', name: '', description: '' })
    setEditOrg(null)
    setCreateOpen(true)
  }

  const openEdit = (org: Organization) => {
    setEditOrg(org)
    reset({ code: org.code, name: org.name, description: org.description || '' })
    setCreateOpen(true)
  }

  const columns: DataTableColumn<Organization>[] = [
    {
      key: 'name',
      header: '组织',
      className: 'min-w-[180px]',
      render: (r) => (
        <div className="flex flex-col">
          <span className="font-medium">{r.name}</span>
          <span className="text-xs text-muted-foreground">{r.code}</span>
        </div>
      ),
    },
    {
      key: 'type',
      header: '类型',
      className: 'w-[90px]',
      render: (r) => (
        <Badge tone={r.type === 'team' ? 'success' : 'neutral'}>
          {r.type === 'team' ? '团队' : '个人'}
        </Badge>
      ),
    },
    {
      key: 'member_count',
      header: '成员',
      className: 'w-[70px]',
      render: (r) => String(r.member_count),
    },
    {
      key: 'project_count',
      header: '项目',
      className: 'hidden md:table-cell w-[70px]',
      render: (r) => String(r.project_count),
    },
    {
      key: 'my_role',
      header: '我的角色',
      className: 'w-[90px]',
      render: (r) => <Badge tone="neutral">{ROLE_LABELS[r.my_role] ?? '成员'}</Badge>,
    },
    {
      key: 'actions',
      header: '操作',
      className: 'w-[280px]',
      render: (r) => (
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => void openProjects(r)} data-icon="inline-start">
            <FolderOpen />
            项目
          </Button>
          {canManage(r) && (
            <>
              <Button size="sm" variant="secondary" onClick={() => void openMembers(r)} data-icon="inline-start">
                <Users />
                成员
              </Button>
              <Button size="sm" variant="secondary" onClick={() => openEdit(r)} data-icon="inline-start">
                <Edit />
                编辑
              </Button>
              {r.type === 'team' && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button size="sm" variant="danger" aria-label={`停用组织 ${r.name}`}>
                      <Trash2 />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>确定停用此组织？</AlertDialogTitle>
                      <AlertDialogDescription>
                        组织「{r.name}」停用后，其项目仍可被项目成员与超管访问，但组织成员入口将不可见。
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>取消</AlertDialogCancel>
                      <AlertDialogAction variant="destructive" onClick={() => void doDisable(r)}>
                        停用
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </>
          )}
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader title="组织管理">
        <Button variant="secondary" size="sm" onClick={refetch} data-icon="inline-start">
          <RotateCcw />
          刷新
        </Button>
        <Button size="sm" onClick={openCreate} data-icon="inline-start">
          <Plus />
          新建组织
        </Button>
      </PageHeader>

      <p className="mb-3 text-sm text-muted-foreground">
        每个用户拥有一个个人组织；可创建团队组织并邀请同事，组织成员默认可见组织下全部项目。
      </p>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        emptyTitle="暂无组织"
        emptyDescription="创建你的第一个团队组织"
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
          <DataTable columns={columns} data={data ?? []} rowKey={(r) => r.id} loading={isLoading} loadingRows={4} />
        )}
      </AsyncState>

      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) { setCreateOpen(false); setEditOrg(null) } }}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>{editOrg ? '编辑组织' : '新建组织'}</DialogTitle>
            <DialogDescription>
              {editOrg ? '修改组织信息' : '创建团队组织后，邀请同事加入协作'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(doSave)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="org-code" className="text-sm font-medium">组织编码</label>
              <Input
                id="org-code"
                placeholder="如：qa-team"
                disabled={!!editOrg}
                {...register('code')}
                className={cn(errors.code && 'border-destructive')}
                aria-describedby={errors.code ? 'org-code-error' : undefined}
              />
              {errors.code && <span id="org-code-error" className="text-xs text-destructive">{errors.code.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="org-name" className="text-sm font-medium">组织名称</label>
              <Input
                id="org-name"
                placeholder="组织显示名"
                {...register('name')}
                className={cn(errors.name && 'border-destructive')}
                aria-describedby={errors.name ? 'org-name-error' : undefined}
              />
              {errors.name && <span id="org-name-error" className="text-xs text-destructive">{errors.name.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="org-description" className="text-sm font-medium">描述</label>
              <Textarea id="org-description" rows={3} {...register('description')} />
            </div>
          </form>
          <DialogFooter>
            <Button variant="secondary" onClick={() => { setCreateOpen(false); setEditOrg(null) }}>
              取消
            </Button>
            <Button disabled={saving} onClick={() => handleSubmit(doSave)()} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Sheet open={membersOrg !== null} onOpenChange={(open) => { if (!open) setMembersOrg(null) }}>
        <SheetContent side="right" className="w-full sm:max-w-[560px]">
          <SheetHeader>
            <SheetTitle>{membersOrg?.name} — 成员管理</SheetTitle>
            <SheetDescription>输入同事的用户名邀请加入（同事需先注册）</SheetDescription>
          </SheetHeader>
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto py-4">
            <div className="flex flex-wrap items-end gap-2">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="org-member-username" className="text-sm font-medium">用户名</label>
                <Input
                  id="org-member-username"
                  className="w-[200px]"
                  placeholder="同事的用户名"
                  value={memberUsername}
                  onChange={(e) => setMemberUsername(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="org-member-role" className="text-sm font-medium">角色</label>
                <Select value={memberRole} onValueChange={setMemberRole}>
                  <SelectTrigger id="org-member-role" className="w-[140px]" aria-label="选择角色">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3">成员</SelectItem>
                    <SelectItem value="2">管理员</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button size="sm" onClick={() => void doAddMember()} data-icon="inline-start">
                <Plus />
                邀请
              </Button>
            </div>

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
                  {membersLoading ? (
                    <TableRow>
                      <TableCell colSpan={3} className="py-6 text-center text-muted-foreground">加载中…</TableCell>
                    </TableRow>
                  ) : members.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="py-6 text-center text-muted-foreground">
                        暂无成员，邀请你的同事吧
                      </TableCell>
                    </TableRow>
                  ) : (
                    members.map((m) => (
                      <TableRow key={m.user_id}>
                        <TableCell>{m.nickname || m.username}（{m.username}）</TableCell>
                        <TableCell><Badge tone="neutral">{ROLE_LABELS[m.role_id] ?? '成员'}</Badge></TableCell>
                        <TableCell>
                          {m.role_id !== 1 && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button size="sm" variant="danger" aria-label={`移除成员 ${m.username}`}>
                                  <Trash2 />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>确定移除？</AlertDialogTitle>
                                  <AlertDialogDescription>将把「{m.username}」移出该组织。</AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>取消</AlertDialogCancel>
                                  <AlertDialogAction variant="destructive" onClick={() => void doRemoveMember(m.user_id)}>
                                    移除
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
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

      <Dialog open={projectsOrg !== null} onOpenChange={(open) => { if (!open) setProjectsOrg(null) }}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>{projectsOrg?.name} — 项目</DialogTitle>
            <DialogDescription>组织成员默认可见这些项目</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            {projectsLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">加载中…</p>
            ) : orgProjects.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">该组织暂无项目</p>
            ) : (
              orgProjects.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium">{p.name}</p>
                    <p className="text-xs text-muted-foreground">{p.code}</p>
                  </div>
                  <Button size="sm" onClick={() => enterProject(p)} data-icon="inline-start">
                    <ArrowRight />
                    进入
                  </Button>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
