import { BarChart3, Bug, Calendar, PieChart, RotateCcw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCallback, useEffect, useState } from 'react'
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
} from 'recharts'
import { format, subDays } from 'date-fns'
import { fetchDashboardStats, type DashboardParams } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'
import type { CaseTypePriority, DashboardStats } from '@/types'

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

// ── 优先级颜色 ──
const PRIORITY_COLORS: Record<string, string> = {
  P0: '#ff4d4f',
  P1: '#fa8c16',
  P2: '#1890ff',
  P3: '#8c8c8c',
}

// 柱状图颜色（用例总数 / 通过 / 失败）
const BAR_COLORS = {
  total: '#1890ff',
  pass: '#52c41a',
  fail: '#ff4d4f',
}

export default function Workbench() {
  const user = useAuthStore((s) => s.user)
  const projects = useAuthStore((s) => s.projects)
  const currentProjectId = useAuthStore((s) => s.currentProjectId)
  const current = projects.find((p) => p.id === currentProjectId)

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(false)

  const today = format(new Date(), 'yyyy-MM-dd')
  const sevenDaysAgo = format(subDays(new Date(), 7), 'yyyy-MM-dd')
  const [preset, setPreset] = useState<PresetKey>('7d')
  const [rangeValue, setRangeValue] = useState<[string, string]>([sevenDaysAgo, today])

  const load = useCallback(async (key: PresetKey, custom: [string, string] | null) => {
    setLoading(true)
    try {
      const { start, end } = getDateRange(key, custom)
      const params: DashboardParams = { start_date: start, end_date: end }
      const d = await fetchDashboardStats(params)
      setStats(d)
    } catch {
      // keep placeholder
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(preset, rangeValue)
  }, [load, preset, rangeValue])

  const handlePresetChange = (val: PresetKey) => {
    setPreset(val)
    const now = new Date()
    if (val === '7d') {
      setRangeValue([format(subDays(now, 7), 'yyyy-MM-dd'), format(now, 'yyyy-MM-dd')])
    } else if (val === '30d') {
      setRangeValue([format(subDays(now, 30), 'yyyy-MM-dd'), format(now, 'yyyy-MM-dd')])
    }
  }

  const s = stats
  const caseTypes = s?.case_type_stats || []
  const priorityData = s?.priority_distribution || []

  // ── 柱状图数据：每个 case_type 一组（总数 / 通过 / 失败） ──
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
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BarChart3 className="size-5" />
          工作台
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {user?.nickname || user?.username} / {current?.name || '未选择项目'}
          </span>
          <Button size="sm" variant="outline" onClick={() => load(preset, rangeValue)} disabled={loading}>
            <RotateCcw className="size-4" />
            刷新
          </Button>
        </div>
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
                className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
              />
              <span className="text-sm text-muted-foreground">至</span>
              <input
                type="date"
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
      {caseTypes.length > 0 && (() => {
        const sumTotal = caseTypes.reduce((s, ct) => s + ct.count, 0)
        const sumPass = caseTypes.reduce((s, ct) => s + ct.execution_pass, 0)
        const sumFail = caseTypes.reduce((s, ct) => s + ct.execution_fail, 0)

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
              {loading ? (
                <div className="flex items-center justify-center h-[340px] text-sm text-muted-foreground">
                  加载中...
                </div>
              ) : (
                <div className="flex">
                  {/* 柱状图主体 */}
                  <div className="flex-1 min-w-0">
                    <ResponsiveContainer width="100%" height={340}>
                      <BarChart
                        data={barData}
                        margin={{ top: 20, right: 8, left: 0, bottom: 8 }}
                        barCategoryGap="30%"
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 13 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <RechartsTooltip content={<BarTooltip />} />
                        <Legend content={() => null} />
                        <Bar dataKey="用例总数" fill={BAR_COLORS.total} radius={[4, 4, 0, 0]} maxBarSize={48}>
                          <LabelList dataKey="用例总数" position="top" style={{ fontSize: 11, fontWeight: 600, fill: BAR_COLORS.total }} />
                        </Bar>
                        <Bar dataKey="执行通过" fill={BAR_COLORS.pass} radius={[4, 4, 0, 0]} maxBarSize={48}>
                          <LabelList dataKey="执行通过" position="top" style={{ fontSize: 11, fontWeight: 600, fill: BAR_COLORS.pass }} />
                        </Bar>
                        <Bar dataKey="执行失败" fill={BAR_COLORS.fail} radius={[4, 4, 0, 0]} maxBarSize={48}>
                          <LabelList dataKey="执行失败" position="top" style={{ fontSize: 11, fontWeight: 600, fill: BAR_COLORS.fail }} />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* 侧边图例（带汇总值） */}
                  <div className="flex items-center justify-center shrink-0 w-[140px]">
                    <div className="bg-muted/50 rounded-lg p-4 border m-2">
                      <div className="text-xs font-semibold mb-2.5">图例</div>
                      {([
                        { label: '用例总数', color: BAR_COLORS.total, value: sumTotal },
                        { label: '执行通过', color: BAR_COLORS.pass, value: sumPass },
                        { label: '执行失败', color: BAR_COLORS.fail, value: sumFail },
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
              )}
            </CardContent>
          </Card>
        )
      })()}

      {/* ─── P0-P3 优先级分布（饼图） ─── */}
      {priorityData.length > 0 && (
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
            {loading ? (
              <div className="flex items-center justify-center h-[240px] text-sm text-muted-foreground">
                加载中...
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {priorityData.map((pd: CaseTypePriority) => {
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
                            labelLine={{ stroke: '#bbb', strokeWidth: 1 }}
                          >
                            {pieData.map((entry) => (
                              <Cell key={entry.name} fill={PRIORITY_COLORS[entry.name]} />
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
                                  style={{ background: PRIORITY_COLORS[key] }}
                                />
                                {key}
                              </span>
                              <span>
                                <span className="font-semibold" style={{ color: PRIORITY_COLORS[key] }}>
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
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
