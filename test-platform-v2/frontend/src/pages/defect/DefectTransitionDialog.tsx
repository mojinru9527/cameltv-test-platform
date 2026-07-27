import { useState } from 'react'
import { ArrowRight, Loader2 } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { STATUS_MAP, statusBadgeClass } from './constants'

interface DefectTransitionDialogProps {
  open: boolean
  currentStatus: string
  targetStatus: string
  onClose: () => void
  onConfirm: (comment: string) => Promise<void>
}

export default function DefectTransitionDialog({
  open,
  currentStatus,
  targetStatus,
  onClose,
  onConfirm,
}: DefectTransitionDialogProps) {
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await onConfirm(comment)
      setComment('')
    } catch {
      // error handled by caller
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setComment('')
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) handleClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>状态流转</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">当前状态:</span>
            <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[currentStatus]?.color)}>
              {STATUS_MAP[currentStatus]?.label || currentStatus || '-'}
            </Badge>
            <ArrowRight className="size-4 text-muted-foreground" />
            <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[targetStatus]?.color)}>
              {STATUS_MAP[targetStatus]?.label || targetStatus}
            </Badge>
          </div>
          <div>
            <label htmlFor="transition-comment" className="text-sm font-medium mb-1 block">备注（可选）</label>
            <Textarea
              id="transition-comment"
              rows={3}
              placeholder="输入流转备注..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>取消</Button>
          <Button onClick={handleConfirm} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin mr-1" />}
            确认流转
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
