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

interface BatchDeleteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  count: number
  projectName: string
  deleting: boolean
  onConfirm: () => void
}

export default function BatchDeleteDialog({
  open,
  onOpenChange,
  count,
  projectName,
  deleting,
  onConfirm,
}: BatchDeleteDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogTitle>确认批量删除用例？</AlertDialogTitle>
          <AlertDialogDescription>
            将从「{projectName}」删除选中的 {count} 条用例。此操作不可撤销，
            服务端将以原子事务处理全部范围，请确认后继续。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={(event) => {
              event.preventDefault()
              onConfirm()
            }}
            disabled={deleting || count === 0}
          >
            {deleting ? '删除中...' : '确认删除'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
