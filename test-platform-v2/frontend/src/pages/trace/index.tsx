import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge, PageShell, SpatialChain, type ChainNode } from '@/ui'
import StatCard from '@/components/StatCard'
import ChartFrame from '@/components/charts/ChartFrame'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useChartColors } from '@/hooks/use-chart-colors'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { fetchCoverage, type CoverageData } from '@/api/trace'
import { FileCheck, Link2, Play, ShieldCheck, Bug, Percent, FileText, Calendar, BarChart3 } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { DOMAIN_GROUP_ORDER, groupDomainLabel } from '@/utils/domainNaming'
import TraceDrilldown from './Drilldown'

// P3-03：用例类型分布轴/图例统一中文标签（兼容后端 canonical 与历史旧值）
const CASE_TYPE_LABEL: Record<string, string> = {
  manual: '功能',
  functional: '功能',
  api: '接口',
  interface: '接口',
  ui: 'UI 自动化',
}

function typeLabel(t: string): string {
  return CASE_TYPE_LABEL[t] || t
}

export default function TracePage() {
  useDocumentTitle('链路追踪')
  const chartColors = useChartColors()
  const { data, isLoading, isError, error, refetch } = useApi<CoverageData>(
    () => fetchCoverage(),
    [],
  )

  return (
    <PageShell
      title="质量追溯"
      description="追踪需求→用例→计划→执行→缺陷→报告的完整质量链路，定位覆盖缺口。"
      glass
    >
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
          // Batch 182（FIX-173-P3-04）：按域覆盖轴按 用户端/运营后台/接口测试/其他 分组聚合，
          // 组内按用例数降序；标签统一走 domainNaming（裸域补前缀展示，如 UGC → 用户端/UGC）。
          const domainGroups = (() => {
            const map = new Map<string, Array<{ domain: string; label: string; count: number }>>()
            for (const [domain, count] of Object.entries(d.by_domain)) {
              const { group, label } = groupDomainLabel(domain)
              if (!map.has(group)) map.set(group, [])
              map.get(group)!.push({ domain, label, count })
            }
            const ordered: Array<{ group: string; items: Array<{ domain: string; label: string; count: number }> }> = []
            for (const group of DOMAIN_GROUP_ORDER) {
              const items = map.get(group)
              if (items) {
                items.sort((a, b) => (b.count - a.count) || a.label.localeCompare(b.label, 'zh-CN'))
                ordered.push({ group, items })
              }
            }
            return ordered
          })()
          return (
            <div className="space-y-6">
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

              {/* ── 空间质量链路 (SpatialChain) ── */}
              {(() => {
                const chainNodes: ChainNode[] = [
                  {
                    id: 'req', label: '需求文档', shortLabel: '需求',
                    count: String(d.requirement_count), status: d.requirements_with_cases > 0 ? '已覆盖' : '待覆盖',
                    progress: d.requirement_coverage_rate ?? 0,
                    tone: (d.requirement_coverage_rate ?? 0) >= 80 ? 'success' : (d.requirement_coverage_rate ?? 0) >= 50 ? 'active' : 'risk',
                    icon: FileText,
                    risk: (d.requirement_coverage_rate ?? 0) < 50,
                  },
                  {
                    id: 'case', label: '测试用例', shortLabel: '用例',
                    count: String(d.total_cases), status: '已就绪',
                    progress: 100,
                    tone: 'success',
                    icon: FileCheck,
                    p0: d.total_cases === 0,
                  },
                  {
                    id: 'plan', label: '测试计划', shortLabel: '计划',
                    count: String(d.cases_in_plans), status: d.cases_in_plans > 0 ? '已编排' : '待编排',
                    progress: d.coverage_rate,
                    tone: d.coverage_rate >= 80 ? 'success' : d.coverage_rate >= 40 ? 'active' : 'risk',
                    icon: Calendar,
                    risk: d.coverage_rate < 40,
                  },
                  {
                    id: 'exec', label: '执行追踪', shortLabel: '执行',
                    count: String(d.cases_executed), status: d.cases_executed > 0 ? '执行中' : '未开始',
                    progress: d.execution_rate,
                    tone: d.execution_rate >= 80 ? 'success' : d.execution_rate >= 30 ? 'active' : 'risk',
                    icon: Play,
                    risk: d.execution_rate < 30,
                  },
                  {
                    id: 'defect', label: '缺陷管理', shortLabel: '缺陷',
                    count: String(d.cases_with_defects), status: d.cases_with_defects > 0 ? '有缺陷' : '无缺陷',
                    progress: d.cases_with_defects > 0 ? Math.min(100, (d.cases_with_defects / Math.max(1, d.cases_executed)) * 100) : 0,
                    tone: d.cases_with_defects === 0 ? 'success' : 'risk',
                    icon: Bug,
                    risk: d.cases_with_defects > 0,
                  },
                  {
                    id: 'report', label: '测试报告', shortLabel: '报告',
                    count: `${d.pass_rate}%`, status: d.pass_rate >= 80 ? '通过' : '关注',
                    progress: d.pass_rate,
                    tone: d.pass_rate >= 80 ? 'success' : 'risk',
                    icon: BarChart3,
                    risk: d.pass_rate < 80,
                  },
                ]
                return (
                  <div className="ui-surface p-4">
                    <SpatialChain
                      nodes={chainNodes}
                      variant="chain"
                    />
                  </div>
                )
              })()}

              {/* ── 追溯下钻── */}
              <TraceDrilldown />

              {/* ── 按用例类型分布 ── */}
              <Card className="ui-surface">
                <CardHeader><CardTitle>用例类型分布</CardTitle></CardHeader>
                <CardContent>
                  <ChartFrame
                    title="用例类型分布"
                    summary={`当前共 ${d.total_cases} 条用例，按功能、接口和 UI 自动化类型分组。`}
                    data={typeChart}
                    columns={[
                      { key: 'name', label: '用例类型' },
                      { key: '数量', label: '数量' },
                    ]}
                  >
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
                  </ChartFrame>
                </CardContent>
              </Card>

              {/* ── 按域分布（Batch 182 / FIX-173-P3-04：按组聚合 + 组内排序）── */}
              <Card className="ui-surface">
                <CardHeader><CardTitle>按域覆盖</CardTitle></CardHeader>
                <CardContent>
                  {domainGroups.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无按域覆盖数据</p>
                  ) : (
                    <div className="space-y-4">
                      {domainGroups.map(({ group, items }) => (
                        <div key={group}>
                          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                            {group}
                            <span className="text-muted-foreground/60">
                              ({items.reduce((sum, item) => sum + item.count, 0)})
                            </span>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {items.map((item) => (
                              <div key={item.domain} className="flex justify-between items-center p-3 rounded-lg border">
                                <span className="truncate text-sm font-medium" title={item.label}>{item.label}</span>
                                <Badge tone="neutral">{item.count}</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* ── 需求覆盖 ── */}
              <Card className="ui-surface">
                <CardHeader><CardTitle>需求覆盖状态</CardTitle></CardHeader>
                <CardContent>
                  <div className="flex items-center gap-8 mb-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-status-info">{d.requirement_count}</div>
                      <div className="text-sm text-muted-foreground">需求文档总数</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-status-success">{d.requirements_with_cases}</div>
                      <div className="text-sm text-muted-foreground">已导入用例的需求</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-status-warning">{d.requirement_count - d.requirements_with_cases}</div>
                      <div className="text-sm text-muted-foreground">待覆盖的需求</div>
                    </div>
                    <div className="text-center">
                      <div
                        className={cn(
                          'text-3xl font-bold',
                          (d.requirement_coverage_rate ?? 0) >= 80
                            ? 'text-status-success'
                            : (d.requirement_coverage_rate ?? 0) >= 50
                              ? 'text-status-warning'
                              : 'text-destructive',
                        )}
                      >
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
    </PageShell>
  )
}
