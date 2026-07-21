import { useState } from 'react'
import { Button } from '@/components/ui/button'

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
    <div className="flex items-center justify-between pt-4 text-sm text-muted-foreground">
      <span>{total != null ? `共 ${total} 条` : ''}</span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
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
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          aria-label="下一页"
        >
          下一页
        </Button>
        <span className="ml-2">跳转到</span>
        <input
          className="w-[50px] rounded-md border px-2 py-1 text-center text-sm"
          placeholder="..."
          value={jumpValue}
          onChange={(e) => setJumpValue(e.target.value.replace(/\D/g, ''))}
          onKeyDown={(e) => { if (e.key === 'Enter') handleJump() }}
        />
        <span>页</span>
        <Button variant="outline" size="sm" onClick={handleJump}>GO</Button>
      </div>
    </div>
  )
}
