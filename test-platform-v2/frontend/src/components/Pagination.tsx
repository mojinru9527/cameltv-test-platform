import { useState } from 'react'
import { Button } from '@/ui'
interface PaginationProps {
  page: number
  totalPages: number
  total?: number
  onChange: (page: number) => void
}

export default function Pagination({ page, totalPages, total, onChange }: PaginationProps) {
  const [jumpValue, setJumpValue] = useState('')

  const handleJump = () => {
    const p = parseInt(jumpValue, 10)
    if (p >= 1 && p <= totalPages) {
      onChange(p)
      setJumpValue('')
    }
  }

  return (
    <div className="flex flex-col gap-3 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
      <span>{total != null ? `共 ${total} 条` : ''}</span>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="上一页"
        >
          上一页
        </Button>
        <span className="pagination-current">{page}</span>
        <span className="text-muted-foreground">/ {totalPages}</span>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          aria-label="下一页"
        >
          下一页
        </Button>
        <span className="ml-2">跳转到</span>
        <input
          className="min-h-9 w-[50px] rounded-md border bg-background px-2 py-1 text-center text-sm text-foreground placeholder:text-muted-foreground"
          placeholder="..."
          value={jumpValue}
          onChange={(e) => setJumpValue(e.target.value.replace(/\D/g, ''))}
          onKeyDown={(e) => { if (e.key === 'Enter') handleJump() }}
          aria-label="跳转页码"
          inputMode="numeric"
        />
        <span>页</span>
        <Button variant="secondary" size="sm" onClick={handleJump} aria-label="确认跳转页码">GO</Button>
      </div>
    </div>
  )
}
