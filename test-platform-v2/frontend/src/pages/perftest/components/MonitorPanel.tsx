import { Button } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/ui'
import { Gauge, Loader2, Play, Square, Wifi, WifiOff } from '@/lib/icons'
import { perfConnectionLabel, type PerfConnectionMode } from '../connectionStatus'
import { METRIC_LABELS } from './perfShared'
import PerfTrendChart from './PerfTrendChart'
import type { PerfSession } from '@/api/perftest'

interface MonitorPanelProps {
  monitoring: boolean
  wsMode: PerfConnectionMode
  reconnectCount: number
  snapshots: { ts: number; elapsed: number; values: Record<string, any> }[]
  latestValues: Record<string, any> | null
  selectedMetrics: string[]
  currentSession: PerfSession | null
  onStartMonitor: () => void
  onStopMonitor: () => void
}

export default function MonitorPanel({
  monitoring,
  wsMode,
  reconnectCount,
  snapshots,
  latestValues,
  selectedMetrics,
  currentSession,
  onStartMonitor,
  onStopMonitor,
}: MonitorPanelProps) {
  return (
    <div className="space-y-4">
      {/* Status bar */}
      <Card>
        <CardContent className="flex items-center gap-4 py-3">
          <div className="flex items-center gap-2">
            {!monitoring ? <WifiOff className="size-4 text-muted-foreground" /> : wsMode === 'websocket' ? <Wifi className="size-4 text-status-success" /> : wsMode === 'polling' ? <WifiOff className="size-4 text-status-warning" /> : <Loader2 className="size-4 animate-spin" />}
            <span className="text-sm">{perfConnectionLabel(monitoring, wsMode)}</span>
            {reconnectCount > 0 && <Badge tone="neutral" className="text-xs">重连 {reconnectCount}/3</Badge>}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              采样: {snapshots.length} 次
              {snapshots.length > 0 && ` · ${snapshots[snapshots.length - 1].elapsed.toFixed(0)}s`}
            </span>
            {monitoring ? (
              <Button onClick={onStopMonitor} variant="danger" size="sm" className="gap-1.5">
                <Square className="size-3" />停止采集
              </Button>
            ) : (
              currentSession && currentSession.status === 'pending' && (
                <Button onClick={onStartMonitor} size="sm" className="gap-1.5">
                  <Play className="size-3" />开始采集
                </Button>
              )
            )}
          </div>
        </CardContent>
      </Card>

      {/* Live values */}
      {latestValues && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {['cpu', 'memory', 'fps', 'jank', 'battery', 'network'].map((key) => {
            let val = '—'
            const data = latestValues[key]
            if (key === 'cpu' && data?.appCpuRate !== undefined) val = `${data.appCpuRate}%`
            else if (key === 'memory' && data?.total !== undefined) val = `${data.total} MB`
            else if (key === 'fps' && data?.fps !== undefined) val = `${data.fps} fps`
            else if (key === 'jank' && data?.jank !== undefined) val = `${data.jank} 次`
            else if (key === 'battery' && data?.level !== undefined) val = `${data.level}% / ${data.temperature}°C`
            else if (key === 'network' && data?.recv !== undefined) val = `${data.recv} KB/s`
            if (key === 'battery' || key === 'network') return null // hide optional ones in MVP
            return (
              <Card key={key} className="p-3">
                <p className="text-xs text-muted-foreground">{METRIC_LABELS[key] ?? key}</p>
                <p className="text-2xl font-bold tabular-nums">{val}</p>
              </Card>
            )
          })}
        </div>
      )}

      {!monitoring && snapshots.length === 0 && (
        <Card>
          <CardContent className="grid min-h-[200px] place-items-center text-sm text-muted-foreground">
            <div className="text-center space-y-2">
              <Gauge className="size-10 mx-auto opacity-30" />
              <p>等待采集开始…</p>
              <p className="text-xs">在"设备与采集"页创建会话并点击"开始采集"</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Realtime trend charts */}
      {snapshots.length > 0 && (
        <PerfTrendChart snapshots={snapshots} selectedMetrics={selectedMetrics} />
      )}
    </div>
  )
}
