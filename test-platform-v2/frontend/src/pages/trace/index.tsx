import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useCallback, useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { fetchCoverage, type CoverageData } from '@/api/trace'
import { FileCheck, Link2, Play, ShieldCheck, Bug, Percent } from '@/lib/icons'

const STAT_CARDS = [
  { key: 'total_cases', label: '用例总数', icon: FileCheck },
  { key: 'cases_in_plans', label: '已纳入计划', icon: Link2 },
  { key: 'cases_executed', label: '已执行', icon: Play },
  { key: 'cases_passed', label: '已通过', icon: ShieldCheck },
  { key: 'cases_with_defects', label: '关联缺陷', icon: Bug },
]

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

  if (loading) return <div className="p-8 text-muted-foreground">加载中...</div>
  if (!data) return <div className="p-8 text-muted-foreground">暂无数据</div>

  // Chart data: by type
  const typeChart = Object.entries(data.by_type).map(([k, v]) => ({ name: typeLabel(k), 数量: v }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">质量追溯</h1>
        <Badge variant="secondary">需求 → 用例 → 计划 → 执行 → 缺陷</Badge>
      </div>

      {/* ── 统计卡片 ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {STAT_CARDS.map(({ key, label, icon: Icon }) => (
          <Card key={key}>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Icon className="size-4" />
                {label}
              </div>
              <div className="text-2xl font-bold mt-1">
                {(data as any)[key] ?? 0}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── 覆盖率指标 ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-sm">计划覆盖率</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Percent className="size-5 text-blue-500" />
              <span className="text-3xl font-bold">{data.coverage_rate}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.cases_in_plans} / {data.total_cases} 条用例已纳入计划
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">执行率</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Percent className="size-5 text-green-500" />
              <span className="text-3xl font-bold">{data.execution_rate}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.cases_executed} / {data.total_cases} 条已执行
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">通过率</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Percent className="size-5 text-emerald-500" />
              <span className="text-3xl font-bold">{data.pass_rate}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              需求覆盖率: {data.requirements_with_cases} / {data.requirement_count}
            </p>
          </CardContent>
        </Card>
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
