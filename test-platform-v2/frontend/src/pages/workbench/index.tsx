import { BarChart3, Bug, Calendar, FileCheck, PieChart, RotateCcw, Percent, Building2, TrendingUp, AlertTriangle } from '@/lib/icons'
import PageHeader from '@/components/PageHeader'
import StatCard from '@/components/StatCard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMemo, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  LabelList,
  LineChart,
  Line,
} from 'recharts'
import { format, subDays } from 'date-fns'
import { fetchDashboardStats, fetchCrossProjectStats } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'
import { useChartColors } from '@/hooks/use-chart-colors'
import { useApi } from '@/hooks/useApi'
import { AsyncState } from '@/components/state'
import type { CaseTypePriority, CrossProjectStats, DashboardStats } from '@/types'

type PresetKey = '7d' | '30d' | 'custom'

// ── 帮助函数 ──

function getDateRange(key: PresetKey, custom: [string, string] | null): { start: string; end: string } {
  const today = new Date()
  if (key === '7d') {
    const start = format(subDays(today, 7), 'yyyy-MM-dd')
    const end = format(today, 'yyyy-MM-dd')
    return { start, end }
  }
  if (key === '30d') {
    const start = format(subDays(today, 30), 'yyyy-MM-dd')
    const end = format(today, 'yyyy-MM-dd')
    return { start, end }
  }
  if (custom && custom[0] && custom[1]) {
    return { start: custom[0], end: custom[1] }
  }
  const start = format(subDays(today, 7), 'yyyy-MM-dd')
  const end = format(today, 'yyyy-MM-dd')
  return { start, end }
}

export default function Workbench() {
  const user = useAuthStore((s) => s.user)
  const projects = useAuthStore((s) => s.projects)
  const currentProjectId = useAuthStore((s) => s.currentProjectId)
  const current = projects.find((p) => p.id === currentProjectId)

  const today = format(new Date(), 'yyyy-MM-dd')
  const sevenDaysAgo = format(subDays(new Date(), 7), 'yyyy-MM-dd')
  const [preset, setPreset] = useState<PresetKey>('7d')
  const [rangeValue, setRangeValue] = useState<[string, string]>([sevenDaysAgo, today])
  const [tab, setTab] = useState<'project' | 'cross'>('project')
  const chartColors = useChartColors()

  // ── Data fetching with useApi ──
  const dateRange = useMemo(() => getDateRange(preset, rangeValue), [preset, rangeValue])

  const { data: stats, isLoading, isRefetching, isError, error, refetch } = useApi<DashboardStats>(
    () => fetchDashboardStats({ start_date: dateRange.start, end_date: dateRange.end }),
    [dateRange.start, dateRange.end]
  )

  const priorityColor = (p: string) =>
    p === 'P0' ? chartColors.p0 : p === 'P1' ? chartColors.p1 : p === 'P2' ? chartColors.p2 : chartColors.p3

  const handlePresetChange = (val: PresetKey) => {
    setPreset(val)
    const now = new Date()
    if (val === '7d') {
      setRangeValue([format(subDays(now, 7), 'yyyy-MM-dd'), format(now, 'yyyy-MM-dd')])
    } else if (val === '30d') {
      setRangeValue([format(subDays(now, 30), 'yyyy-MM-dd'), format(now, 'yyyy-MM-dd')])
    }
  }

  // ── Derived chart data (computed from stats, safe even when undefined) ──
  const s = stats
  const caseTypes = s?.case_type_stats || []
  const priorityData = s?.priority_distribution || []

  const barData = caseTypes.map((ct) => ({
    name: ct.label,
    caseType: ct.case_type,
    用例总数: ct.count,
    执行通过: ct.execution_pass,
    执行失败: ct.execution_fail,
    通过率: `${ct.pass_rate}%`,
    失败率: `${ct.fail_rate}%`,
  }))

  // ── Custom Tooltip for bar chart ──
  function BarTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null
    const entry = barData.find((d) => d.name === label)
    return (
      <div className="bg-background rounded-lg border px-3.5 py-2.5 shadow-md text-sm">
        <div className="font-semibold mb-1.5">{label}</div>
        {payload.map((p: any) => (
          <div key={p.dataKey} className="text-[13px]" style={{ color: p.color }}>
            {p.dataKey}：{p.value}
          </div>
        ))}
        {entry && (
          <div className="mt-1 text-xs text-muted-foreground">
            通过率 {entry.通过率} ｜ 失败率 {entry.失败率}
          </div>
        )}
      </div>
    )
  }

  // ── Pie custom tooltip ──
  function PieTooltip({ active, payload, total }: any) {
    if (!active || !payload?.length) return null
    const d = payload[0]
    const t = total ?? 0
    const pct = t > 0 ? ((d.value / t) * 100).toFixed(1) : '0'
    return (
      <div className="bg-background rounded-lg border px-3 py-2 shadow-md text-sm">
        <span
          className="inline-block size-2.5 rounded-sm mr-2"
          style={{ background: d.payload.fill }}
        />
        {d.name}：{d.value}（{pct}%）
      </div>
    )
  }

  return (
    <div>
      {/* 标题栏 */}
      <PageHeader title="工作台" icon={BarChart3}>
        <span className="text-sm text-muted-foreground">
          {user?.nickname || user?.username} / {current?.name || '未选择项目'}
        </span>
        <Button size="sm" variant="outline" onClick={refetch} disabled={isLoading || isRefetching}>
          <RotateCcw className="size-4" />
          刷新
        </Button>
      </PageHeader>

      <Tabs value={tab} onValueChange={(v) => setTab(v as any)} className="mb-4">
        <TabsList>
          <TabsTrigger value="project">项目概览</TabsTrigger>
          <TabsTrigger value="cross">多项目概览</TabsTrigger>
        </TabsList>

        <TabsContent value="project">
          <AsyncState
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={stats}
            onRetry={refetch}
            skeletonType="card"
            loadingText="加载仪表盘数据..."
            emptyTitle="暂无仪表盘数据"
          >
        {(_s) => {
          const _caseTypes = _s.case_type_stats || []
          const _priorityData = _s.priority_distribution || []

          return (
            <>
              {/* ─── 摘要指标 ─── */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                <StatCard icon={FileCheck} label="用例总数" value={_s.total_cases} variant="glass" />
                <StatCard icon={BarChart3} label="测试计划" value={_s.total_plans} variant="glass" />
                <StatCard icon={Percent} label="通过率" value={`${_s.pass_rate}%`} variant="glass" />
                <StatCard icon={Bug} label="接口用例" value={_s.api_cases} variant="glass" />
              </div>

              {/* ─── 时间范围筛选 ─── */}
              <Card size="sm" className="mb-4">
                <CardContent>
                  <div className="flex items-center gap-4 flex-wrap">
                    <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                      <Calendar className="size-4" />
                      时间范围：
                    </span>
                    <div className="inline-flex items-center rounded-lg border border-input bg-muted p-0.5">
                      {(['7d', '30d', 'custom'] as PresetKey[]).map((key) => {
                        const label = key === '7d' ? '近 7 天' : key === '30d' ? '近 30 天' : '自定义'
                        return (
                          <Button
                            key={key}
                            variant={preset === key ? 'default' : 'ghost'}
                            size="sm"
                            className="h-7"
                            onClick={() => handlePresetChange(key)}
                          >
                            {label}
                          </Button>
                        )
                      })}
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="date"
                        value={rangeValue[0]}
                        onChange={(e) => {
                          setPreset('custom')
                          setRangeValue([e.target.value, rangeValue[1]])
                        }}
                        aria-label="开始日期"
                        className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
                      />
                      <span className="text-sm text-muted-foreground">至</span>
                      <input
                        type="date"
                        aria-label="结束日期"
                        value={rangeValue[1]}
                        onChange={(e) => {
                          setPreset('custom')
                          setRangeValue([rangeValue[0], e.target.value])
                        }}
                        className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* ─── 项目概览（柱状图） ─── */}
              {_caseTypes.length > 0 && (() => {
                const sumTotal = _caseTypes.reduce((sum, ct) => sum + ct.count, 0)
                const sumPass = _caseTypes.reduce((sum, ct) => sum + ct.execution_pass, 0)
                const sumFail = _caseTypes.reduce((sum, ct) => sum + ct.execution_fail, 0)

                return (
                  <Card size="sm" className="mb-4">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-1.5">
                        <BarChart3 className="size-4" />
                        项目概览
                        <span className="text-xs text-muted-foreground font-normal ml-2">
                          按用例类型分类统计 · 柱状图
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex">
                        {/* 柱状图主体 */}
                        <div className="flex-1 min-w-0">
                          <ResponsiveContainer width="100%" height={340}>
                            <BarChart
                              data={barData}
                              margin={{ top: 20, right: 8, left: 0, bottom: 8 }}
                              barCategoryGap="30%"
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridColor} />
                              <XAxis dataKey="name" tick={{ fontSize: 13 }} />
                              <YAxis tick={{ fontSize: 12 }} />
                              <RechartsTooltip content={<BarTooltip />} />
                              <Legend content={() => null} />
                              <Bar dataKey="用例总数" fill={chartColors.barTotal} radius={[4, 4, 0, 0]} maxBarSize={48}>
                                <LabelList dataKey="用例总数" position="top" style={{ fontSize: 11, fontWeight: 600, fill: chartColors.barTotal }} />
                              </Bar>
                              <Bar dataKey="执行通过" fill={chartColors.barPass} radius={[4, 4, 0, 0]} maxBarSize={48}>
                                <LabelList dataKey="执行通过" position="top" style={{ fontSize: 11, fontWeight: 600, fill: chartColors.barPass }} />
                              </Bar>
                              <Bar dataKey="执行失败" fill={chartColors.barFail} radius={[4, 4, 0, 0]} maxBarSize={48}>
                                <LabelList dataKey="执行失败" position="top" style={{ fontSize: 11, fontWeight: 600, fill: chartColors.barFail }} />
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>

                        {/* 侧边图例（带汇总值） */}
                        <div className="flex items-center justify-center shrink-0 w-[140px]">
                          <div className="bg-muted/50 rounded-lg p-4 border m-2">
                            <div className="text-xs font-semibold mb-2.5">图例</div>
                            {([
                              { label: '用例总数', color: chartColors.barTotal, value: sumTotal },
                              { label: '执行通过', color: chartColors.barPass, value: sumPass },
                              { label: '执行失败', color: chartColors.barFail, value: sumFail },
                            ]).map((item) => (
                              <div key={item.label} className="flex items-center mb-2 text-xs">
                                <span
                                  className="inline-block size-3 rounded-sm mr-2 shrink-0"
                                  style={{ background: item.color }}
                                />
                                <span className="text-muted-foreground mr-1.5">{item.label}</span>
                                <span className="font-semibold text-[13px]" style={{ color: item.color }}>
                                  {item.value}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })()}

              {/* ─── P0-P3 优先级分布（饼图） ─── */}
              {_priorityData.length > 0 && (
                <Card size="sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-1.5">
                      <PieChart className="size-4" />
                      用例优先级分布
                      <span className="text-xs text-muted-foreground font-normal ml-2">
                        P0-P3 按用例类型统计 · 饼图
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {_priorityData.map((pd: CaseTypePriority) => {
                        const pieData = [
                          { name: 'P0', value: pd.p0 },
                          { name: 'P1', value: pd.p1 },
                          { name: 'P2', value: pd.p2 },
                          { name: 'P3', value: pd.p3 },
                        ].filter((d) => d.value > 0)

                        if (pieData.length === 0) {
                          return (
                            <div key={pd.case_type} className="flex flex-col items-center justify-center py-10 text-center">
                              <span className="text-sm" style={{ color: pd.color }}>{pd.label}</span>
                              <span className="mt-2 text-muted-foreground/60 text-sm">暂无数据</span>
                            </div>
                          )
                        }

                        return (
                          <div key={pd.case_type}>
                            {/* 类型标题 */}
                            <div className="text-center mb-1">
                              <span className="text-sm font-semibold" style={{ color: pd.color }}>
                                {pd.label}
                              </span>
                              <span className="text-xs text-muted-foreground ml-1.5">
                                （{pd.total} 个）
                              </span>
                            </div>

                            {/* 饼图 */}
                            <ResponsiveContainer width="100%" height={240}>
                              <RechartsPieChart>
                                <Pie
                                  data={pieData}
                                  dataKey="value"
                                  nameKey="name"
                                  cx="50%"
                                  cy="50%"
                                  innerRadius={45}
                                  outerRadius={85}
                                  paddingAngle={2}
                                  label={({ name, value }) => `${name}: ${value}`}
                                  labelLine={{ stroke: chartColors.labelLineColor, strokeWidth: 1 }}
                                >
                                  {pieData.map((entry) => (
                                    <Cell key={entry.name} fill={priorityColor(entry.name)} />
                                  ))}
                                </Pie>
                                <RechartsTooltip
                                  content={({ active, payload }) => (
                                    <PieTooltip active={active} payload={payload} total={pd.total} />
                                  )}
                                />
                              </RechartsPieChart>
                            </ResponsiveContainer>

                            {/* 每个饼图自己的图例 */}
                            <div className="bg-muted/50 rounded-md p-2.5 border mt-1">
                              {([
                                { key: 'P0' as const, val: pd.p0 },
                                { key: 'P1' as const, val: pd.p1 },
                                { key: 'P2' as const, val: pd.p2 },
                                { key: 'P3' as const, val: pd.p3 },
                              ]).map(({ key, val }) => {
                                const pct = pd.total > 0 ? ((val / pd.total) * 100).toFixed(1) : '0'
                                return (
                                  <div
                                    key={key}
                                    className="flex items-center justify-between mb-1 text-xs last:mb-0"
                                  >
                                    <span className="text-muted-foreground flex items-center gap-1.5">
                                      <span
                                        className="inline-block size-2.5 rounded-sm"
                                        style={{ background: priorityColor(key) }}
                                      />
                                      {key}
                                    </span>
                                    <span>
                                      <span className="font-semibold" style={{ color: priorityColor(key) }}>
                                        {val}
                                      </span>
                                      <span className="text-muted-foreground ml-1 text-[11px]">{pct}%</span>
                                    </span>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )
        }}
      </AsyncState>
        </TabsContent>

        <TabsContent value="cross">
          <CrossProjectDashboard dateRange={dateRange} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ── Cross-Project Dashboard (V2.5) ──

function CrossProjectDashboard({ dateRange }: { dateRange: { start: string; end: string } }) {
  const chartColors = useChartColors()

  const { data: crossStats, isLoading, isError, error, refetch } = useApi<CrossProjectStats>(
    () => fetchCrossProjectStats({ start_date: dateRange.start, end_date: dateRange.end }),
    [dateRange.start, dateRange.end]
  )

  return (
    <AsyncState
      isLoading={isLoading}
      isError={isError}
      error={error}
      data={crossStats}
      onRetry={refetch}
      skeletonType="card"
      loadingText="加载跨项目数据..."
      emptyTitle="暂无跨项目数据"
    >
      {(stats) => (
        <div className="space-y-4">
          {/* Aggregate Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard icon={Building2} label="项目总数" value={stats.aggregate.total_projects} variant="glass" />
            <StatCard icon={FileCheck} label="用例总数" value={stats.aggregate.total_cases} variant="glass" />
            <StatCard icon={BarChart3} label="测试计划" value={stats.aggregate.total_plans} variant="glass" />
            <StatCard icon={Percent} label="整体通过率" value={`${stats.aggregate.overall_pass_rate}%`} variant="glass" />
            <StatCard icon={Bug} label="接口用例" value={stats.aggregate.total_api_cases} variant="glass" />
            <StatCard icon={AlertTriangle} label="缺陷总数" value={stats.aggregate.total_defects} variant="glass" />
          </div>

          {/* Per-Project Cards */}
          {stats.per_project.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {stats.per_project.map((proj) => (
                <Card key={proj.project_id} size="sm">
                  <CardHeader>
                    <CardTitle className="text-sm">{proj.project_name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="text-muted-foreground">用例: <span className="font-semibold text-foreground">{proj.total_cases}</span></div>
                      <div className="text-muted-foreground">计划: <span className="font-semibold text-foreground">{proj.total_plans}</span></div>
                      <div className="text-muted-foreground">通过率: <span className="font-semibold text-green-600">{proj.pass_rate}%</span></div>
                      <div className="text-muted-foreground">缺陷: <span className="font-semibold text-red-600">{proj.defect_count}</span></div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Trends Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card size="sm">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-1.5">
                  <TrendingUp className="size-4" />
                  整体通过率趋势（近 7 天）
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={stats.trends.pass_rate}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridColor} />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                    <RechartsTooltip formatter={(value: any) => [`${value}%`, '通过率']} />
                    <Line type="monotone" dataKey="pass_rate" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card size="sm">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-1.5">
                  <Bug className="size-4" />
                  缺陷趋势（近 7 天）
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={stats.trends.defects}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridColor} />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                    <RechartsTooltip formatter={(value: any) => [value, '新增缺陷']} />
                    <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </AsyncState>
  )
}
