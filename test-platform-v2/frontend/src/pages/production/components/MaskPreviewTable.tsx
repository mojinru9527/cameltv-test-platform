import { Badge, Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { displayValue } from '../utils'

export interface MaskEntry {
  entity?: string | null
  entity_type?: string | null
  field?: string | null
  field_pattern?: string | null
  strategy?: string | null
  classification?: string | null
  priority?: number | null
  [key: string]: unknown
}

const STRATEGY_TONE: Record<string, { label: string; color: string }> = {
  REDACT: { label: 'REDACT', color: 'bg-status-danger-muted text-status-danger' },
  HASH: { label: 'HASH', color: 'bg-status-warning-muted text-status-warning' },
  TOKENIZE: { label: 'TOKENIZE', color: 'bg-status-info-muted text-status-info' },
  FAKE: { label: 'FAKE', color: 'bg-status-info-muted text-status-info' },
  PRESERVE: { label: 'PRESERVE', color: 'bg-status-success-muted text-status-success' },
}

interface MaskPreviewTableProps {
  masks: MaskEntry[]
  loading?: boolean
}

/** Render a template's masked nodes / attributes table. */
export function MaskPreviewTable({ masks, loading = false }: MaskPreviewTableProps) {
  if (loading) return <Skeleton className="h-24 w-full" />
  if (masks.length === 0) {
    return <p className="py-4 text-sm text-muted-foreground">暂无脱敏规则预览。</p>
  }

  return (
    <div className="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>实体</TableHead>
            <TableHead>字段</TableHead>
            <TableHead>分类</TableHead>
            <TableHead>策略</TableHead>
            <TableHead>优先级</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {masks.map((mask, i) => {
            const strategy = mask.strategy ?? mask.field_pattern ?? ''
            const strategyMeta = STRATEGY_TONE[strategy]
            const entity = mask.entity ?? mask.entity_type ?? '-'
            const field = mask.field ?? mask.field_pattern ?? '-'
            return (
              <TableRow key={`${entity}-${field}-${i}`}>
                <TableCell className="max-w-[22ch] truncate font-mono text-xs">{displayValue(entity)}</TableCell>
                <TableCell className="max-w-[24ch] truncate font-mono text-xs">{displayValue(field)}</TableCell>
                <TableCell className="max-w-[24ch] truncate text-muted-foreground">
                  {displayValue(mask.classification ?? '-')}
                </TableCell>
                <TableCell>
                  <Badge tone="neutral" className={strategyMeta?.color}>{strategyMeta?.label ?? displayValue(strategy)}</Badge>
                </TableCell>
                <TableCell className="font-mono">#{mask.priority ?? '-'}</TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
