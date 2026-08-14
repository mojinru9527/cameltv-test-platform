import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Pagination from '@/components/Pagination'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

interface Props {
  paginatedDomains: any[]
  page: number
  totalPages: number
  total: number
  onPageChange: (page: number) => void
}

export default function RequirementDomainCoverageTable({
  paginatedDomains,
  page,
  totalPages,
  total,
  onPageChange,
}: Props) {
  return (
    <Card size="sm" className="ui-surface">
      <CardHeader className="border-b pb-3">
        <CardTitle className="text-sm">需求域与用例覆盖</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">业务域</TableHead>
              <TableHead className="w-[90px]">用例数</TableHead>
              <TableHead>模块</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedDomains.map((item: any) => (
              <TableRow key={item.domain}>
                <TableCell className="font-medium">{item.domain}</TableCell>
                <TableCell>{item.count}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 flex-wrap">
                    {(item.modules || []).slice(0, 8).map((m: any) => (
                      <Badge key={m.module} tone="neutral">
                        {m.module} ({m.count})
                      </Badge>
                    ))}
                    {(item.modules || []).length > 8 && (
                      <Badge tone="neutral">+{(item.modules || []).length - 8}</Badge>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          onChange={onPageChange}
        />
      </CardContent>
    </Card>
  )
}
