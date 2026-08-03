import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, Badge } from '@/ui'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { fetchRequirements } from '@/api/requirement'
import {
  fetchCaseTrace,
  fetchRequirementTrace,
  type CaseTrace,
  type RequirementTraceSummary,
} from '@/api/trace'
import { FileText, Bug, Play, Link2, RefreshCw } from '@/lib/icons'

const statusTone: Record<string, 'default' | 'secondary' | 'ghost' | 'destructive' | 'outline'> = {
  pass: 'secondary',
  fail: 'destructive',
  skip: 'outline',
  block: 'destructive',
}

export default function TraceDrilldown() {
  const [selectedDoc, setSelectedDoc] = useState<number | null>(null)
  const [selectedCase, setSelectedCase] = useState<number | null>(null)

  const docs = useApi<any>(() => fetchRequirements({ page: 1, page_size: 50 }), [])
  const docList = useMemo(
    () => (docs.data?.items ?? docs.data ?? []) as Array<{ id: number; title: string }>,
    [docs.data],
  )

  const reqTrace = useApi<RequirementTraceSummary>(
    () => (selectedDoc ? fetchRequirementTrace(selectedDoc) : Promise.resolve(null as any)),
    [selectedDoc],
  )

  const caseTrace = useApi<CaseTrace>(
    () => (selectedCase ? fetchCaseTrace(selectedCase) : Promise.resolve(null as any)),
    [selectedCase],
  )

  return (
    <Card className="ui-surface">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Link2 className="size-4" />
          追溯下钻
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* ── 需求文档选择 ── */}
        <AsyncState
          isLoading={docs.isLoading}
          isError={docs.isError}
          error={docs.error}
          data={docList}
          onRetry={docs.refetch}
          emptyTitle="暂无需求文档"
        >
          {(items) => (
            <div className="flex flex-wrap gap-2">
              {items.map((d: any) => (
                <Button
                  key={d.id}
                  size="sm"
                  variant={selectedDoc === d.id ? 'primary' : 'secondary'}
                  onClick={() => {
                    setSelectedDoc(d.id)
                    setSelectedCase(null)
                  }}
                >
                  <FileText className="size-3.5" data-icon="inline-start" />
                  {d.title}
                </Button>
              ))}
            </div>
          )}
        </AsyncState>

        {/* ── 需求覆盖明细 ── */}
        {selectedDoc && (
          <AsyncState
            isLoading={reqTrace.isLoading}
            isError={reqTrace.isError}
            error={reqTrace.error}
            data={reqTrace.data}
            onRetry={reqTrace.refetch}
            emptyTitle="该文档暂无覆盖数据"
          >
            {(d: RequirementTraceSummary) => (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2 text-sm">
                  <Badge>用例 {d.total_cases}</Badge>
                  <Badge>计划 {d.cases_in_plans}</Badge>
                  <Badge>执行 {d.cases_executed}</Badge>
                  <Badge>通过 {d.cases_passed}</Badge>
                  <Badge variant="outline">覆盖率 {d.coverage_rate}%</Badge>
                  <Badge variant="outline">执行率 {d.execution_rate}%</Badge>
                  <Badge variant="outline">通过率 {d.pass_rate}%</Badge>
                </div>
                <div className="max-h-64 overflow-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="p-2">用例</th>
                        <th className="p-2">域/模块</th>
                        <th className="p-2">优先级</th>
                        <th className="p-2">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(d.cases ?? []).slice(0, 100).map((c: any) => (
                        <tr key={c.id ?? c.case_id} className="border-b last:border-0 hover:bg-muted/40">
                          <td className="p-2">{c.title ?? c.case_id}</td>
                          <td className="p-2 text-muted-foreground">{c.domain}/{c.module}</td>
                          <td className="p-2"><Badge variant="outline">{c.priority}</Badge></td>
                          <td className="p-2">
                            <Button size="sm" variant="ghost" onClick={() => setSelectedCase(c.id)} disabled={!c.id}>
                              <RefreshCw className="size-3" data-icon="inline-start" />
                              下钻
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </AsyncState>
        )}

        {/* ── 用例追溯链 ── */}
        {selectedCase && (
          <AsyncState
            isLoading={caseTrace.isLoading}
            isError={caseTrace.isError}
            error={caseTrace.error}
            data={caseTrace.data}
            onRetry={caseTrace.refetch}
            emptyTitle="该用例暂无追溯链"
          >
            {(c: CaseTrace) => (
              <div className="space-y-3 rounded-md border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{c.case_title}</span>
                  <Badge variant="outline">{c.case_id}</Badge>
                  <Badge variant="outline">{c.domain}/{c.module}</Badge>
                  {c.priority && <Badge variant="outline">{c.priority}</Badge>}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">
                      <Play className="size-3" /> 计划与执行
                    </p>
                    <div className="space-y-1">
                      {(c.plans ?? []).map((pl) => (
                        <div key={pl.plan_id} className="rounded border px-2 py-1 text-xs">
                          <span className="font-medium">{pl.plan_name}</span>
                          {' '}
                          <Badge variant={statusTone[pl.last_status] ?? 'outline'}>{pl.last_status}</Badge>
                          <div className="mt-1 text-muted-foreground">
                            {(pl.executions ?? []).map((ex) => (
                              <span key={ex.id} className="mr-2">
                                {new Date(ex.executed_at ?? '').toLocaleString()} → {ex.status}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">
                      <Bug className="size-3" /> 关联缺陷
                    </p>
                    <div className="space-y-1">
                      {(c.defects ?? []).map((df) => (
                        <div key={df.defect_id} className="rounded border px-2 py-1 text-xs">
                          <span className="font-medium">{df.title}</span>
                          {' '}
                          <Badge variant="outline">{df.severity}</Badge>
                          <Badge variant={statusTone[df.status] ?? 'outline'}>{df.status}</Badge>
                        </div>
                      ))}
                      {(c.defects ?? []).length === 0 && (
                        <p className="text-xs text-muted-foreground">无关联缺陷</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </AsyncState>
        )}
      </CardContent>
    </Card>
  )
}
