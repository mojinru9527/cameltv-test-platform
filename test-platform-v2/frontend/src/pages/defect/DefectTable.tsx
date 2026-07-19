import { Edit, Eye, Trash2 } from '@/lib/icons'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import Pagination from '@/components/Pagination'
import { AsyncState } from '@/components/state'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { deleteDefect } from '@/api/defect'
import type { DefectItem } from '@/types'
import { SEVERITY_MAP, STATUS_MAP, severityBadgeClass, statusBadgeClass } from './constants'
import { toast } from 'sonner'

interface DefectTableProps {
  data: any
  isLoading: boolean
  isError: boolean
  error: Error | null
  onRetry: () => void
  page: number
  onPageChange: (page: number) => void
  onDetail: (item: DefectItem) => void
  onEdit: (item: DefectItem) => void
  onDeleted: () => void
  canUpdate: boolean
  canDelete: boolean
}

export default function DefectTable({
  data,
  isLoading,
  isError,
  error,
  onRetry,
  page,
  onPageChange,
  onDetail,
  onEdit,
  onDeleted,
  canUpdate,
  canDelete,
}: DefectTableProps) {
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (deleteTarget == null) return
    setDeleting(true)
    try {
      await deleteDefect(deleteTarget)
      toast.success('已删除')
      setDeleteTarget(null)
      onDeleted()
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AsyncState
      isLoading={isLoading}
      isError={isError}
      error={error}
      data={data}
      onRetry={onRetry}
      loadingVariant="skeleton"
      skeletonType="table"
      loadingRows={5}
      emptyTitle="暂无缺陷"
      emptyDescription="当前筛选条件下没有缺陷记录"
    >
      {(d) => (
        <>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[160px]">编号</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead className="w-[100px]">状态</TableHead>
                  <TableHead className="w-[100px]">处理人</TableHead>
                  <TableHead className="w-[150px]">关联用例</TableHead>
                  <TableHead className="w-[170px]">创建时间</TableHead>
                  <TableHead className="w-[200px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((r: any) => (
                  <TableRow key={r.id}>
                    <TableCell className="max-w-[160px] truncate">{r.defect_id}</TableCell>
                    <TableCell className="max-w-0">
                      <div className="flex items-center gap-1.5">
                        <button
                          className="text-primary hover:underline text-left truncate cursor-pointer bg-transparent border-0 p-0"
                          onClick={() => onDetail(r)}
                        >
                          {r.title}
                        </button>
                        <Badge variant="outline" className={severityBadgeClass(SEVERITY_MAP[r.severity]?.color)}>
                          {SEVERITY_MAP[r.severity]?.label || r.severity}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[r.status]?.color)}>
                        {STATUS_MAP[r.status]?.label || r.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[100px] truncate">{r.assignee_name}</TableCell>
                    <TableCell className="max-w-[150px] truncate">{r.case_title}</TableCell>
                    <TableCell>{r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button size="xs" variant="outline" onClick={() => onDetail(r)}>
                          <Eye className="size-3" />
                          详情
                        </Button>
                        {canUpdate && (
                          <Button size="xs" variant="outline" onClick={() => onEdit(r)}>
                            <Edit className="size-3" />
                            编辑
                          </Button>
                        )}
                        {canDelete && (
                          <AlertDialog open={deleteTarget === r.id} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
                            <AlertDialogTrigger asChild>
                              <Button
                                size="xs"
                                variant="outline"
                                className="text-destructive border-destructive/20 hover:bg-destructive/10"
                                onClick={() => setDeleteTarget(r.id)}
                              >
                                <Trash2 className="size-3" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>确定删除此缺陷？</AlertDialogTitle>
                                <AlertDialogDescription>此操作不可撤销。</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel onClick={() => setDeleteTarget(null)}>取消</AlertDialogCancel>
                                <AlertDialogAction onClick={handleDelete} disabled={deleting}>
                                  {deleting ? '删除中...' : '确定删除'}
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <Pagination
            page={d.page}
            totalPages={Math.max(1, Math.ceil(d.total / d.page_size))}
            total={d.total}
            onChange={(p) => onPageChange(p)}
          />
        </>
      )}
    </AsyncState>
  )
}
