import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/ui'
import { AlertCircle, BarChart3, CheckCircle2 } from '@/lib/icons'
import { METRIC_LABELS, STATUS_LABELS } from './perfShared'
import MetricStatCard from './MetricStatCard'
import type { CompareResponse, PerfReport } from '@/api/perftest'

interface ReportPanelProps {
  report: PerfReport | null
  compareResult: CompareResponse | null
}

export default function ReportPanel({ report, compareResult }: ReportPanelProps) {
  return (
    <div className="space-y-4">
      {/* Report */}
      {report && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              采集报告: {report.session.session_id}
              <Badge tone="neutral" className="ml-2 text-xs">
                {STATUS_LABELS[report.session.status] ?? report.session.status}
              </Badge>
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              {report.session.device_name} · {report.session.pkg_name} · {report.session.platform} · {report.session.actual_duration_s || report.session.duration}s
            </p>
          </CardHeader>
          <CardContent>
            {report.metrics.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无指标数据</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {report.metrics.map((m) => (
                  <MetricStatCard key={m.metric_type} stat={m} />
                ))}
              </div>
            )}

            {report.anomalies.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-2">异常事件 ({report.anomalies.length})</h4>
                <div className="space-y-1">
                  {report.anomalies.map((a, i) => (
                    <div key={i} className="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm">
                      <AlertCircle className="size-4 text-status-warning shrink-0" />
                      <span className="text-xs text-muted-foreground font-mono">{new Date(a.timestamp * 1000).toLocaleTimeString()}</span>
                      <Badge tone="neutral" className="text-xs">{a.event_type}</Badge>
                      <span className="text-xs flex-1 truncate">{a.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Compare */}
      {compareResult && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              对比: {compareResult.session_a.session_id} vs {compareResult.session_b.session_id}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {compareResult.deltas.map((d) => (
                <Card key={d.metric_type} className={`p-3 ${d.significant ? (d.direction === 'degraded' ? 'border-status-danger-border bg-status-danger-muted' : 'border-status-success-border bg-status-success-muted') : ''}`}>
                  <p className="text-xs text-muted-foreground">{METRIC_LABELS[d.metric_type] ?? d.metric_type}</p>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-lg font-bold tabular-nums">{d.session_a_mean}</span>
                    <span className="text-xs text-muted-foreground">vs</span>
                    <span className="text-sm tabular-nums">{d.session_b_mean}</span>
                  </div>
                  <p className={`text-xs mt-0.5 ${
                    d.direction === 'degraded' ? 'text-status-danger' :
                    d.direction === 'improved' ? 'text-status-success' :
                    'text-muted-foreground'
                  }`}>
                    {d.delta_absolute > 0 ? '+' : ''}{d.delta_absolute} ({d.delta_percent > 0 ? '+' : ''}{d.delta_percent}%)
                    {d.significant && (
                      <span className="ml-1 inline-flex items-center gap-1">
                        {d.direction === 'degraded'
                          ? <><AlertCircle className="size-3.5" />恶化</>
                          : d.direction === 'improved'
                            ? <><CheckCircle2 className="size-3.5" />改善</>
                            : null}
                      </span>
                    )}
                  </p>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {!report && !compareResult && (
        <Card>
          <CardContent className="grid min-h-[160px] place-items-center text-sm text-muted-foreground">
            <div className="text-center space-y-2">
              <BarChart3 className="size-10 mx-auto opacity-30" />
              <p>在"历史记录"中点击"报告"查看单次采集报告</p>
              <p className="text-xs">或选择 2 个会话进行对比</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
