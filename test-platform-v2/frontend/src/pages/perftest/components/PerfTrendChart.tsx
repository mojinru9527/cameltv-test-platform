import { useMemo } from 'react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import ChartFrame from '@/components/charts/ChartFrame'

const CHART_COLORS: Record<string, string> = {
  fps: '#10b981',    // emerald-500
  cpu: '#3b82f6',    // blue-500
  memory: '#f59e0b', // amber-500
  jank: '#ef4444',   // red-500
}

interface PerfTrendChartProps {
  snapshots: { ts: number; elapsed: number; values: Record<string, any> }[]
  selectedMetrics: string[]
}

export default function PerfTrendChart({ snapshots, selectedMetrics }: PerfTrendChartProps) {
  const chartData = useMemo(() => {
    // Take last 120 points to keep the chart readable
    const recent = snapshots.slice(-120)
    return recent.map((s) => {
      const fpsVal = s.values?.fps?.fps ?? s.values?.fps ?? null
      const cpuVal = s.values?.cpu?.appCpuRate ?? s.values?.cpu ?? null
      const memVal = s.values?.memory?.total ?? s.values?.memory?.pss ?? s.values?.memory ?? null
      const jankVal = s.values?.jank?.jank ?? s.values?.jank ?? null
      return {
        elapsed: Number(s.elapsed.toFixed(1)),
        fps: fpsVal != null ? Number(fpsVal) : null,
        cpu: cpuVal != null ? Number(cpuVal) : null,
        memory: memVal != null ? Number(memVal) : null,
        jank: jankVal != null ? Number(jankVal) : null,
      }
    })
  }, [snapshots])

  const visibleMetrics = selectedMetrics.filter((m) => m !== 'startup' && m !== 'anr')

  if (visibleMetrics.length === 0) return null

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* FPS chart — primary, always full-width on mobile */}
      {(visibleMetrics.includes('fps') || visibleMetrics.includes('jank')) && (
        <Card className={visibleMetrics.length > 2 ? 'lg:col-span-2' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">帧率 FPS</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartFrame
              title="帧率 FPS"
              summary={`共 ${chartData.length} 个采样点，展示帧率与卡顿次数随采集时间的变化。`}
              data={chartData}
              columns={[
                { key: 'elapsed', label: '采集时间', format: (value) => `${value}s` },
                { key: 'fps', label: 'FPS', format: (value) => value == null ? '—' : `${value} fps` },
                { key: 'jank', label: '卡顿', format: (value) => value == null ? '—' : `${value} 次` },
              ]}
            >
              <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                  <XAxis
                    dataKey="elapsed"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v: number) => `${v}s`}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    yAxisId="fps"
                    domain={[0, 'auto']}
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 12 }}
                    labelFormatter={(v: any) => `${v}s`}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {visibleMetrics.includes('fps') && (
                    <Line
                      yAxisId="fps"
                      type="monotone"
                      dataKey="fps"
                      stroke={CHART_COLORS.fps}
                      strokeWidth={2}
                      dot={false}
                      name="FPS"
                      unit=" fps"
                      connectNulls
                    />
                  )}
                  {visibleMetrics.includes('jank') && (
                    <Line
                      yAxisId="fps"
                      type="stepAfter"
                      dataKey="jank"
                      stroke={CHART_COLORS.jank}
                      strokeWidth={1.5}
                      dot={false}
                      name="Jank"
                      unit=" 次"
                      connectNulls
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
              </div>
            </ChartFrame>
          </CardContent>
        </Card>
      )}

      {/* CPU chart */}
      {visibleMetrics.includes('cpu') && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">CPU 使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartFrame
              title="CPU 使用率"
              summary={`共 ${chartData.length} 个采样点，单位为百分比。`}
              data={chartData}
              columns={[
                { key: 'elapsed', label: '采集时间', format: (value) => `${value}s` },
                { key: 'cpu', label: 'CPU 使用率', format: (value) => value == null ? '—' : `${value}%` },
              ]}
            >
              <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                  <XAxis
                    dataKey="elapsed"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v: number) => `${v}s`}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 12 }}
                    labelFormatter={(v: any) => `${v}s`}
                  />
                  <Line
                    type="monotone"
                    dataKey="cpu"
                    stroke={CHART_COLORS.cpu}
                    strokeWidth={2}
                    dot={false}
                    name="CPU"
                    unit="%"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
              </div>
            </ChartFrame>
          </CardContent>
        </Card>
      )}

      {/* Memory chart */}
      {visibleMetrics.includes('memory') && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">内存</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartFrame
              title="内存"
              summary={`共 ${chartData.length} 个采样点，单位为 MB。`}
              data={chartData}
              columns={[
                { key: 'elapsed', label: '采集时间', format: (value) => `${value}s` },
                { key: 'memory', label: '内存', format: (value) => value == null ? '—' : `${value} MB` },
              ]}
            >
              <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                  <XAxis
                    dataKey="elapsed"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v: number) => `${v}s`}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    domain={[0, 'auto']}
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 12 }}
                    labelFormatter={(v: any) => `${v}s`}
                  />
                  <Line
                    type="monotone"
                    dataKey="memory"
                    stroke={CHART_COLORS.memory}
                    strokeWidth={2}
                    dot={false}
                    name="内存"
                    unit=" MB"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
              </div>
            </ChartFrame>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
