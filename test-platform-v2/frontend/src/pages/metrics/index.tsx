import { useEffect, useState } from 'react'
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, PageShell } from '@/ui'
import { compareVersions, getOperationsMetrics, type OperationsMetrics } from '@/api/versionTask'

/** B13 运营指标看板 + 跨版本对比。 */
export default function MetricsPage() {
  const [m, setM] = useState<OperationsMetrics | null>(null)
  const [verA, setVerA] = useState('')
  const [verB, setVerB] = useState('')
  const [compare, setCompare] = useState<{ a: Record<string, unknown>; b: Record<string, unknown> } | null>(null)

  useEffect(() => {
    getOperationsMetrics().then(setM).catch(() => {})
  }, [])

  async function handleCompare() {
    if (!verA.trim() || !verB.trim()) return
    setCompare(await compareVersions(verA.trim(), verB.trim()))
  }

  const cards = m ? [
    { label: '回归人天', value: m.regression_person_days, unit: '人天' },
    { label: '提测→放行周期', value: m.cycle_avg_days, unit: '天' },
    { label: '漏测（缺陷）', value: m.missed_defects, unit: '个' },
    { label: '周活跃任务', value: m.weekly_active, unit: '个' },
  ] : []

  return (
    <PageShell title="运营指标">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader>
              <CardTitle className="text-sm">{c.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{c.value}</div>
              <div className="text-xs text-muted-foreground">{c.unit}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>跨版本对比</CardTitle>
          <CardDescription>对比两个版本的覆盖/结论/缺陷</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Input className="w-32" placeholder="版本 A" value={verA} onChange={(e) => setVerA(e.target.value)} />
            <Input className="w-32" placeholder="版本 B" value={verB} onChange={(e) => setVerB(e.target.value)} />
            <Button variant="primary" onClick={handleCompare}>对比</Button>
          </div>
          {compare && (
            <div className="space-y-2 text-sm">
              {(["a", "b"] as const).map((k) => {
                const row = compare[k]
                return (
                  <div key={k} className="flex items-center gap-2 rounded border p-2">
                    <Badge variant="secondary">{row.version as string}</Badge>
                    <span>通过率 {row.pass_rate as number}%</span>
                    <span className="text-muted-foreground">结论 {row.verdict as string}</span>
                    <span className="text-muted-foreground">缺陷 {row.defect_count as number}</span>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </PageShell>
  )
}
