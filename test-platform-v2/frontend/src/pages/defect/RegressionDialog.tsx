import { Button, Input } from '@/ui'
import { useState } from 'react'
import { Loader2 } from '@/lib/icons'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/ui'

interface RegressionDialogProps {
  open: boolean
  defectId: number
  onClose: () => void
  onSubmit: (fixedSha: string) => Promise<void>
}

export default function RegressionDialog({ open, defectId, onClose, onSubmit }: RegressionDialogProps) {
  const [fixedSha, setFixedSha] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleConfirm = async () => {
    const sha = fixedSha.trim()
    if (sha.length < 7) {
      setError('请输入至少 7 位的修复 commit SHA')
      return
    }
    setError('')
    setLoading(true)
    try {
      await onSubmit(sha)
      setFixedSha('')
      onClose()
    } catch {
      setError('回归发起失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onClose() }}>
      <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>一键回归 · 缺陷 #{defectId}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <label className="text-sm text-muted-foreground" htmlFor="fixed-sha">
            修复 commit SHA
          </label>
          <Input
            id="fixed-sha"
            value={fixedSha}
            placeholder="例如 abc1234def"
            onChange={(event) => setFixedSha(event.target.value)}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            取消
          </Button>
          <Button onClick={handleConfirm} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            发起回归
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
