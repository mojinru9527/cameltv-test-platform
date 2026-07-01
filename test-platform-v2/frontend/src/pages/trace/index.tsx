import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import PageHeader from '@/components/PageHeader'
import StatCard from '@/components/StatCard'
import EmptyState from '@/components/EmptyState'
import { SkeletonPage } from '@/components/ui/skeleton'
import { useCallback, useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { fetchCoverage, type CoverageData } from '@/api/trace'
import { FileCheck, Link2, Play, ShieldCheck, Bug, Percent } from '@/lib/icons'

export default function TracePage() {
  const [data, setData] = useState<CoverageData | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetchCoverage()
      setData(r)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <div className="p-6"><SkeletonPage /></div>
  if (!data) return (
    <div className="p-6">
      <EmptyState
        title="暂无追溯数据"
        description="请先创建用例和测试计划，系统将自动追踪质量链路"
      />
    </div>
  )

  // Chart data: by type
  const typeChart = Object.entries(data.by_type).map(([k, v]) => ({ name: typeLabel(k), 数量: v }))

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="质量追溯"
        description="需求 → 用例 → 计划 → 执行 → 缺陷，全链路质量可视化"
      />

      {/* ── 统计卡片 ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard icon={FileCheck} label="用例总数" value={data.total_cases} variant="glass" />
        <StatCard icon={Link2} label="已纳入计划" value={data.cases_in_plans} variant="glass" />
        <StatCard icon={Play} label="已执行" value={data.cases_executed} variant="glass" />
        <StatCard icon={ShieldCheck} label="已通过" value={data.cases_passed} variant="glass" />
        <StatCard icon={Bug} label="关联缺陷" value={data.cases_with_defects} variant="glass" />
      </div>

      {/* ── 覆盖率指标 ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={Percent}
          label="计划覆盖率"
          value={`${data.coverage_rate}%`}
          trend={`${data.cases_in_plans} / ${data.total_cases} 条用例已纳入计划`}
          variant="glass"
        />
        <StatCard
          icon={Percent}
          label="执行率"
          value={`${data.execution_rate}%`}
          trend={`${data.cases_executed} / ${data.total_cases} 条已执行`}
          variant="glass"
        />
        <StatCard
          icon={Percent}
          label="通过率"
          value={`${data.pass_rate}%`}
          trend={`需求覆盖: ${data.requirements_with_cases} / ${data.requirement_count}`}
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
              <Bar dataKey="数量" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* ── 按域分布 ── */}
      <Card>
        <CardHeader><CardTitle>按域覆盖</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(data.by_domain).map(([domain, count]) => (
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
          <div className="flex items-center gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{data.requirement_count}</div>
              <div className="text-sm text-muted-foreground">需求文档总数</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{data.requirements_with_cases}</div>
              <div className="text-sm text-muted-foreground">已导入用例的需求</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600">{data.requirement_count - data.requirements_with_cases}</div>
              <div className="text-sm text-muted-foreground">待覆盖的需求</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function typeLabel(t: string): string {
  const m: Record<string, string> = { manual: '功能', api: '接口', ui: '自动化' }
  return m[t] || t
}
