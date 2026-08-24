import { Button } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Trash2 } from '@/lib/icons'

interface CaseBatchToolbarProps {
  selectedCount: number
  canUpdate: boolean
  canDelete: boolean
  batchPriority: string
  setBatchPriority: (v: string) => void
  batchUpdating: boolean
  batchDeleting: boolean
  onBatchUpdate: () => void
  onOpenBatchDeleteDialog: () => void
  onCancelSelection: () => void
}

export default function CaseBatchToolbar({
  selectedCount,
  canUpdate,
  canDelete,
  batchPriority,
  setBatchPriority,
  batchUpdating,
  batchDeleting,
  onBatchUpdate,
  onOpenBatchDeleteDialog,
  onCancelSelection,
}: CaseBatchToolbarProps) {
  return (
    <div className="flex items-center gap-2 rounded-md border bg-accent/30 px-3 py-2">
      <span className="text-sm font-medium">已选 {selectedCount} 条</span>
      {canUpdate && <Select value={batchPriority || undefined} onValueChange={setBatchPriority}>
        <SelectTrigger className="w-[100px]" size="sm" aria-label="批量设置优先级">
          <SelectValue placeholder="优先级" />
        </SelectTrigger>
        <SelectContent position="popper">
          {['P0','P1','P2','P3'].map(v => (
            <SelectItem key={v} value={v}>{v}</SelectItem>
          ))}
        </SelectContent>
      </Select>}
      {canUpdate && <Button size="sm" variant="secondary" onClick={onBatchUpdate} disabled={batchUpdating || !batchPriority}>
        {batchUpdating ? '更新中…' : '批量更新'}
      </Button>}
      <div className="flex-1" />
      {canDelete && <Button size="sm" variant="danger" onClick={onOpenBatchDeleteDialog} disabled={batchDeleting}>
        <Trash2 className="size-3.5" data-icon="inline-start" />
        {batchDeleting ? '删除中…' : `批量删除 (${selectedCount})`}
      </Button>}
      <Button size="sm" variant="ghost" onClick={onCancelSelection}>取消</Button>
    </div>
  )
}
