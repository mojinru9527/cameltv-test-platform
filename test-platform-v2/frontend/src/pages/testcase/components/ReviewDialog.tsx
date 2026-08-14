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
import { Textarea } from '@/components/ui/textarea'

interface ReviewDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  action: string
  comment: string
  setComment: (v: string) => void
  reviewing: boolean
  onReview: () => void
}

export default function ReviewDialog({
  open,
  onOpenChange,
  action,
  comment,
  setComment,
  reviewing,
  onReview,
}: ReviewDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogTitle>
            {action === 'submit' ? '提交评审' : action === 'approve' ? '通过评审' : '驳回用例'}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {action === 'submit'
              ? '确认将此用例提交评审？提交后状态变为"已提交"。'
              : action === 'approve'
                ? '确认通过此用例的评审？'
                : '请填写驳回原因：'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {(action === 'reject') && (
          <div className="my-3">
            <Textarea
              placeholder="驳回原因..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
            />
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => onOpenChange(false)}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={onReview}
            variant={action === 'reject' ? 'destructive' : 'default'}
            disabled={reviewing || (action === 'reject' && !comment.trim())}
          >
            {reviewing ? '处理中...' : action === 'submit' ? '确认提交' : action === 'approve' ? '确认通过' : '确认驳回'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
