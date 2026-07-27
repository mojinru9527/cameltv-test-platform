import { Plus, RotateCcw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import SearchInput from '@/components/SearchInput'
import { SEVERITY_MAP, STATUS_MAP } from './constants'

interface DefectFilterBarProps {
  severity: string | undefined
  status: string | undefined
  keyword: string
  onSeverityChange: (v: string | undefined) => void
  onStatusChange: (v: string | undefined) => void
  onKeywordChange: (v: string) => void
  onRefresh: () => void
  canCreate: boolean
  onCreate: () => void
}

export default function DefectFilterBar({
  severity,
  status,
  keyword,
  onSeverityChange,
  onStatusChange,
  onKeywordChange,
  onRefresh,
  canCreate,
  onCreate,
}: DefectFilterBarProps) {
  return (
    <div className="flex items-center gap-2 mb-4 flex-wrap">
      <Select
        value={severity ?? '__all__'}
        onValueChange={(v) => onSeverityChange(v === '__all__' ? undefined : v)}
      >
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="严重程度" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">全部</SelectItem>
          {Object.entries(SEVERITY_MAP).map(([k, v]) => (
            <SelectItem key={k} value={k}>{v.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={status ?? '__all__'}
        onValueChange={(v) => onStatusChange(v === '__all__' ? undefined : v)}
      >
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">全部</SelectItem>
          {Object.entries(STATUS_MAP).map(([k, v]) => (
            <SelectItem key={k} value={k}>{v.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <SearchInput
        value={keyword}
        onChange={(v) => onKeywordChange(v)}
        onSearch={onRefresh}
        placeholder="搜索缺陷标题"
        inputClassName="w-[220px]"
        clearable
      />

      <Button variant="outline" size="default" onClick={onRefresh}>
        <RotateCcw className="size-4" />
        刷新
      </Button>
      {canCreate && (
        <Button onClick={onCreate} variant="neon">
          <Plus className="size-4" />
          新建缺陷
        </Button>
      )}
    </div>
  )
}
