import { Badge } from '@/ui'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { CoverageReport } from '@/types'

interface Props {
  report: CoverageReport
}

export default function AiCoveragePanel({ report }: Props) {
  return (
    <div className="flex-1 overflow-y-auto pr-1 max-h-[55vh] space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <Badge tone="neutral" className="border-status-success-border bg-status-success-muted text-status-success">
          覆盖率 {(report.coverage_rate * 100).toFixed(1)}%
        </Badge>
        <span className="text-xs text-muted-foreground">
          已覆盖 {report.covered_fp}/{report.total_fp} 功能点 · 缺口 {report.gap_count}
        </span>
      </div>
      {report.gap_count > 0 && (
        <div className="border rounded-lg p-2 space-y-1.5">
          <p className="text-xs font-medium text-status-warning">覆盖缺口</p>
          {report.gaps.map((g, i) => (
            <div key={`${g.module}-${g.function_point}-${i}`} className="text-xs flex items-center gap-1.5">
              <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning">缺口</Badge>
              <span>{g.module} · {g.function_point}</span>
            </div>
          ))}
        </div>
      )}
      {report.matrix.length > 0 ? (
        <div className="border rounded-lg overflow-auto">
          <Table className="min-w-[560px]">
            <TableHeader>
              <TableRow>
                <TableHead>模块</TableHead>
                <TableHead>功能点</TableHead>
                <TableHead className="text-center">覆盖</TableHead>
                <TableHead className="text-center">用例数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.matrix.map((row, i) => (
                <TableRow key={`${row.module}-${row.function_point}-${i}`}>
                  <TableCell className="text-xs">{row.module || '-'}</TableCell>
                  <TableCell className="text-xs">{row.function_point || '-'}</TableCell>
                  <TableCell className="text-center">
                    <Badge
                      tone="neutral"
                      className={row.covered
                        ? 'border-status-success-border bg-status-success-muted text-status-success'
                        : 'border-status-danger-border bg-status-danger-muted text-status-danger'}
                    >
                      {row.covered ? '已覆盖' : '未覆盖'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center text-xs">{row.case_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground py-4 text-center">暂无覆盖矩阵数据</p>
      )}
    </div>
  )
}
