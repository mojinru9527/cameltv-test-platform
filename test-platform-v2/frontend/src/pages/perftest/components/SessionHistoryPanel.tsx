import { Button } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/ui'
import { RefreshCw } from '@/lib/icons'
import { STATUS_LABELS, STATUS_TONES } from './perfShared'
import type { PerfSession } from '@/api/perftest'

interface SessionHistoryPanelProps {
  sessions: PerfSession[]
  totalSessions: number
  compareA: number | null
  compareB: number | null
  setCompareA: (id: number | null) => void
  setCompareB: (id: number | null) => void
  onLoadReport: (sessionId: number) => void
  onCompare: () => void
  onRefresh: () => void
}

export default function SessionHistoryPanel({
  sessions,
  totalSessions,
  compareA,
  compareB,
  setCompareA,
  setCompareB,
  onLoadReport,
  onCompare,
  onRefresh,
}: SessionHistoryPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-2 flex-row items-center justify-between">
        <CardTitle className="text-base">采集记录 ({totalSessions})</CardTitle>
        <Button variant="ghost" size="icon" onClick={onRefresh} aria-label="刷新采集记录">
          <RefreshCw className="size-4" aria-hidden="true" />
        </Button>
      </CardHeader>
      <CardContent>
        {sessions.length === 0 ? (
          <div className="grid min-h-[120px] place-items-center text-sm text-muted-foreground">
            暂无采集记录
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-4">会话ID</th>
                  <th className="py-2 pr-4">平台</th>
                  <th className="py-2 pr-4">设备</th>
                  <th className="py-2 pr-4">应用</th>
                  <th className="py-2 pr-4">时长</th>
                  <th className="py-2 pr-4">状态</th>
                  <th className="py-2 pr-4">时间</th>
                  <th className="py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id} className="border-b">
                    <td className="py-2 pr-4 font-mono text-xs">{s.session_id}</td>
                    <td className="py-2 pr-4">{s.platform}</td>
                    <td className="py-2 pr-4 max-w-[120px] truncate" title={s.device_name}>{s.device_name}</td>
                    <td className="py-2 pr-4 font-mono text-xs max-w-[150px] truncate" title={s.pkg_name}>{s.pkg_name}</td>
                    <td className="py-2 pr-4">{s.actual_duration_s || s.duration}s</td>
                    <td className="py-2 pr-4">
                      <Badge tone={STATUS_TONES[s.status] ?? 'neutral'} className="text-xs">
                        {STATUS_LABELS[s.status] ?? s.status}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4 text-xs text-muted-foreground">
                      {s.created_at ? new Date(s.created_at).toLocaleString() : ''}
                    </td>
                    <td className="py-2">
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" onClick={() => onLoadReport(s.id)} disabled={s.status !== 'completed'}>
                          报告
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => {
                          setCompareA(compareA === s.id ? null : s.id)
                          if (compareA && compareA !== s.id) setCompareB(s.id)
                        }}>
                          {compareA === s.id ? '已选A' : compareB === s.id ? '已选B' : '对比'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {compareA && compareB && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-sm text-muted-foreground">已选择 #{compareA} vs #{compareB}</span>
            <Button size="sm" onClick={onCompare}>执行对比</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
