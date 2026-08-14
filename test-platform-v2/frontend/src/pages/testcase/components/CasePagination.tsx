import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Pagination from '@/components/Pagination'

interface CasePaginationProps {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}

export default function CasePagination({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: CasePaginationProps) {
  return (
    <div className="flex shrink-0 flex-col items-stretch justify-between gap-3 border-t pt-2 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">每页</span>
        <Select value={String(pageSize)} onValueChange={(v) => { onPageSizeChange(Number(v)); onPageChange(1) }}>
          <SelectTrigger className="w-[80px]" size="sm" aria-label="每页显示条数"><SelectValue /></SelectTrigger>
          <SelectContent position="popper">
            {[20, 50, 100].map(n => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">条</span>
      </div>
      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        onChange={onPageChange}
      />
    </div>
  )
}
