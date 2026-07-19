import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { createDomain, createModule, deleteDomain, deleteModule } from '@/api/testcase'
import type { TestCaseDomainCategory, TestCaseModuleCategory } from '@/api/testcase'
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
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ChevronRight, Plus, Trash2 } from '@/lib/icons'

interface Props {
  open: boolean
  domains: TestCaseDomainCategory[]
  onClose: () => void
  onChanged: () => Promise<void> | void
}

type DeleteTarget =
  | { type: 'domain'; domainId: number; name: string; caseCount: number }
  | { type: 'module'; domainId: number; moduleId: number; name: string; caseCount: number }

function categoryId(id: number | undefined): number | null {
  return Number.isInteger(id) && (id as number) > 0 ? (id as number) : null
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

interface DomainNodeProps {
  domain: TestCaseDomainCategory
  onDeleteDomain: (domain: TestCaseDomainCategory, domainId: number) => void
  onDeleteModule: (
    domain: TestCaseDomainCategory,
    module: TestCaseModuleCategory,
    domainId: number,
    moduleId: number,
  ) => void
}

function DomainNode({ domain, onDeleteDomain, onDeleteModule }: DomainNodeProps) {
  const [open, setOpen] = useState(false)
  const domainId = categoryId(domain.id)

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-lg border">
      <div className="flex items-center gap-2 bg-muted/40 px-2 py-1.5">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="h-8 min-w-0 flex-1 justify-start px-1.5">
            <ChevronRight
              className={`mr-1.5 size-4 shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
            />
            <span className="truncate font-medium">{domain.domain}</span>
            <span className="ml-2 shrink-0 text-xs text-muted-foreground">
              {domain.count} 条用例
            </span>
          </Button>
        </CollapsibleTrigger>
        <Button
          size="icon-xs"
          variant="ghost"
          className="text-destructive hover:bg-destructive/10"
          title={domainId ? `删除域 ${domain.domain}` : '分类接口尚未更新，暂不能删除'}
          disabled={!domainId}
          onClick={() => domainId && onDeleteDomain(domain, domainId)}
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>

      <CollapsibleContent>
        <div className="divide-y border-t bg-background pl-8">
          {domain.modules.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">暂无模块</p>
          ) : domain.modules.map((module: TestCaseModuleCategory) => {
            const moduleId = categoryId(module.id)
            return (
              <div
                key={module.id ?? `${domain.domain}-${module.module}`}
                className="flex items-center gap-2 px-3 py-2 text-sm"
              >
                <span className="min-w-0 flex-1 truncate">{module.module}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {module.count} 条用例
                </span>
                <Button
                  size="icon-xs"
                  variant="ghost"
                  className="text-destructive hover:bg-destructive/10"
                  title={domainId && moduleId ? `删除模块 ${module.module}` : '分类接口尚未更新，暂不能删除'}
                  disabled={!domainId || !moduleId}
                  onClick={() => domainId && moduleId && onDeleteModule(domain, module, domainId, moduleId)}
                >
                  <Trash2 className="size-3" />
                </Button>
              </div>
            )
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export default function CategoryManagerDialog({ open, domains, onClose, onChanged }: Props) {
  const [domainName, setDomainName] = useState('')
  const [moduleName, setModuleName] = useState('')
  const [selectedDomainId, setSelectedDomainId] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)

  const selectableDomains = domains.filter((domain) => categoryId(domain.id) !== null)
  const hasLegacyCategoryData = domains.some(
    (domain) => categoryId(domain.id) === null
      || domain.modules.some((module: TestCaseModuleCategory) => categoryId(module.id) === null),
  )

  useEffect(() => {
    if (!selectableDomains.some((domain) => String(domain.id) === selectedDomainId)) {
      setSelectedDomainId(selectableDomains[0] ? String(selectableDomains[0].id) : '')
    }
  }, [selectableDomains, selectedDomainId])

  const addDomain = async () => {
    const name = domainName.trim()
    if (!name) {
      toast.error('请输入域名称')
      return
    }
    setSaving(true)
    try {
      await createDomain(name)
      setDomainName('')
      toast.success('域已新增')
      await onChanged()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  const addModule = async () => {
    const name = moduleName.trim()
    const domainId = Number(selectedDomainId)
    if (!Number.isInteger(domainId) || domainId <= 0) {
      toast.error('请先选择所属域')
      return
    }
    if (!name) {
      toast.error('请输入模块名称')
      return
    }
    setSaving(true)
    try {
      await createModule(domainId, name)
      setModuleName('')
      toast.success('模块已新增')
      await onChanged()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      if (deleteTarget.type === 'domain') {
        await deleteDomain(deleteTarget.domainId)
        toast.success('域及其关联用例已删除')
      } else {
        await deleteModule(deleteTarget.moduleId)
        toast.success('模块及其关联用例已删除')
      }
      setDeleteTarget(null)
      await onChanged()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose() }}>
        <DialogContent className="sm:max-w-[620px]">
          <DialogHeader>
            <DialogTitle>模块分类管理</DialogTitle>
            <DialogDescription>先新增域，再在域下维护可供用例选择的模块。</DialogDescription>
          </DialogHeader>

          {hasLegacyCategoryData && (
            <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              分类接口尚未更新，当前分类缺少 ID，已暂停删除和新增模块操作。
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2 rounded-lg border p-3">
              <label htmlFor="new-domain" className="text-sm font-medium">新增域</label>
              <div className="flex gap-2">
                <Input
                  id="new-domain"
                  value={domainName}
                  onChange={(event) => setDomainName(event.target.value)}
                  onKeyDown={(event) => { if (event.key === 'Enter') void addDomain() }}
                  placeholder="请输入域名称"
                />
                <Button size="sm" onClick={addDomain} disabled={saving || !domainName.trim()}>
                  <Plus className="size-3.5" />新增
                </Button>
              </div>
            </div>

            <div className="space-y-2 rounded-lg border p-3">
              <label htmlFor="new-module" className="text-sm font-medium">新增模块</label>
              <Select value={selectedDomainId || undefined} onValueChange={setSelectedDomainId}>
                <SelectTrigger className="w-full" size="sm" aria-label="所属域">
                  <SelectValue placeholder="选择所属域" />
                </SelectTrigger>
                <SelectContent position="popper" align="start" className="z-[100]">
                  {selectableDomains.map((domain) => (
                    <SelectItem key={domain.id} value={String(domain.id)}>{domain.domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex gap-2">
                <Input
                  id="new-module"
                  value={moduleName}
                  onChange={(event) => setModuleName(event.target.value)}
                  onKeyDown={(event) => { if (event.key === 'Enter') void addModule() }}
                  placeholder="请输入模块名称"
                  disabled={!selectedDomainId}
                />
                <Button
                  size="sm"
                  onClick={addModule}
                  disabled={saving || !selectedDomainId || !moduleName.trim()}
                >
                  <Plus className="size-3.5" />新增
                </Button>
              </div>
            </div>
          </div>

          <div className="max-h-[42vh] space-y-2 overflow-y-auto pr-1">
            {domains.length === 0 ? (
              <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                暂无域，请先新增域。
              </p>
            ) : domains.map((domain) => (
              <DomainNode
                key={domain.id ?? domain.domain}
                domain={domain}
                onDeleteDomain={(targetDomain, domainId) => setDeleteTarget({
                  type: 'domain',
                  domainId,
                  name: targetDomain.domain,
                  caseCount: targetDomain.count,
                })}
                onDeleteModule={(targetDomain, module, domainId, moduleId) => setDeleteTarget({
                  type: 'module',
                  domainId,
                  moduleId,
                  name: `${targetDomain.domain} / ${module.module}`,
                  caseCount: module.count,
                })}
              />
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={(nextOpen) => { if (!nextOpen) setDeleteTarget(null) }}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>
              确认删除{deleteTarget?.type === 'domain' ? '域' : '模块'}？
            </AlertDialogTitle>
            <AlertDialogDescription>
              “{deleteTarget?.name}”及其关联的 {deleteTarget?.caseCount ?? 0} 条用例将被逻辑删除，列表中不再显示。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
            <AlertDialogAction variant="destructive" disabled={deleting} onClick={confirmDelete}>
              {deleting ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
