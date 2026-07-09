import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import PageHeader from '@/components/PageHeader'
import StatCard from '@/components/StatCard'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useChartColors } from '@/hooks/use-chart-colors'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { fetchCoverage, type CoverageData } from '@/api/trace'
import { FileCheck, Link2, Play, ShieldCheck, Bug, Percent } from '@/lib/icons'

export default function TracePage() {
  const chartColors = useChartColors()
  const { data, isLoading, isError, error, refetch } = useApi<CoverageData>(
    () => fetchCoverage(),
    [],
  )

  return (
    <div className="p-6">
      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        fullPage
        loadingVariant="skeleton"
        skeletonType="page"
        emptyTitle="暂无追溯数据"
        emptyDescription="请先创建用例和测试计划，系统将自动追踪质量链路"
      >
        {(d) => {
          const typeChart = Object.entries(d.by_type).map(([k, v]) => ({ name: typeLabel(k), 数量: v }))
          return (
            <div className="space-y-6">
              <PageHeader
                title="质量追溯"
                description="需求 → 用例 → 计划 → 执行 → 缺陷，全链路质量可视化"
              />

              {/* ── 统计卡片 ── */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <StatCard icon={FileCheck} label="用例总数" value={d.total_cases} variant="glass" />
                <StatCard icon={Link2} label="已纳入计划" value={d.cases_in_plans} variant="glass" />
                <StatCard icon={Play} label="已执行" value={d.cases_executed} variant="glass" />
                <StatCard icon={ShieldCheck} label="已通过" value={d.cases_passed} variant="glass" />
                <StatCard icon={Bug} label="关联缺陷" value={d.cases_with_defects} variant="glass" />
              </div>

              {/* ── 覆盖率指标 ── */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                  icon={Percent}
                  label="计划覆盖率"
                  value={`${d.coverage_rate}%`}
                  trend={`${d.cases_in_plans} / ${d.total_cases} 条用例已纳入计划`}
                  variant="glass"
                />
                <StatCard
                  icon={Percent}
                  label="执行率"
                  value={`${d.execution_rate}%`}
                  trend={`${d.cases_executed} / ${d.total_cases} 条已执行`}
                  variant="glass"
                />
                <StatCard
                  icon={Percent}
                  label="通过率"
                  value={`${d.pass_rate}%`}
                  trend={`需求覆盖: ${d.requirements_with_cases} / ${d.requirement_count}`}
                  variant="glass"
                />
              </div>

              {/* ── 按用例类型分布 ── */}
              <Card>
                <CardHeader><CardTitle>用例类型分布</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={typeChart}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="数量" fill={chartColors.chart1} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* ── 按域分布 ── */}
              <Card>
                <CardHeader><CardTitle>按域覆盖</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(d.by_domain).map(([domain, count]) => (
                      <div key={domain} className="flex justify-between items-center p-3 rounded-lg border">
                        <span className="text-sm font-medium">{domain || '未分类'}</span>
                        <Badge variant="outline">{count}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* ── 需求覆盖 ── */}
              <Card>
                <CardHeader><CardTitle>需求覆盖状态</CardTitle></CardHeader>
                <CardContent>
                  <div className="flex items-center gap-8 mb-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">{d.requirement_count}</div>
                      <div className="text-sm text-muted-foreground">需求文档总数</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-green-600">{d.requirements_with_cases}</div>
                      <div className="text-sm text-muted-foreground">已导入用例的需求</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-orange-600">{d.requirement_count - d.requirements_with_cases}</div>
                      <div className="text-sm text-muted-foreground">待覆盖的需求</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold" style={{ color: (d.requirement_coverage_rate ?? 0) >= 80 ? chartColors.barPass : (d.requirement_coverage_rate ?? 0) >= 50 ? chartColors.chart4 : chartColors.barFail }}>
                        {d.requirement_coverage_rate ?? 0}%
                      </div>
                      <div className="text-sm text-muted-foreground">需求覆盖率</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )
        }}
      </AsyncState>
    </div>
  )
}

function typeLabel(t: string): string {
  const m: Record<string, string> = { manual: '功能', api: '接口', ui: '自动化' }
  return m[t] || t
}
