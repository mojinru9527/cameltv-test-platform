import { Button } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/ui'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/ui'
import { Loader2, Play, RefreshCw, Smartphone } from '@/lib/icons'
import { METRIC_LABELS, STATUS_LABELS } from './perfShared'
import type { PerfDevice, PerfSession } from '@/api/perftest'

interface DeviceCollectionPanelProps {
  devices: PerfDevice[]
  loading: boolean
  collectorUnavailable: boolean
  selectedDevice: PerfDevice | null
  setSelectedDevice: (device: PerfDevice | null) => void
  selectedApp: string
  setSelectedApp: (app: string) => void
  selectedMetrics: string[]
  setSelectedMetrics: (metrics: string[]) => void
  duration: number
  setDuration: (duration: number) => void
  currentSession: PerfSession | null
  onCreateSession: () => void
  onStartMonitor: () => void
  onRefreshDevices: () => void
}

export default function DeviceCollectionPanel({
  devices,
  loading,
  collectorUnavailable,
  selectedDevice,
  setSelectedDevice,
  selectedApp,
  setSelectedApp,
  selectedMetrics,
  setSelectedMetrics,
  duration,
  setDuration,
  currentSession,
  onCreateSession,
  onStartMonitor,
  onRefreshDevices,
}: DeviceCollectionPanelProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* Device list */}
      <Card>
        <CardHeader className="pb-2 flex-row items-center justify-between">
          <CardTitle className="text-base">已连接设备</CardTitle>
          <Button variant="ghost" size="icon" onClick={onRefreshDevices} disabled={loading} aria-label="刷新设备列表">
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          </Button>
        </CardHeader>
        <CardContent>
          {loading && devices.length === 0 ? (
            <div className="grid min-h-[120px] place-items-center"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
          ) : collectorUnavailable ? (
            <div className="grid min-h-[120px] place-items-center text-sm text-muted-foreground">
              <p>采集器恢复后，可在此选择真实设备。</p>
            </div>
          ) : devices.length === 0 ? (
            <div className="grid min-h-[120px] place-items-center text-sm text-muted-foreground">
              <div className="text-center space-y-2">
                <Smartphone className="size-8 mx-auto opacity-30" />
                <p>未检测到设备</p>
                <p className="text-xs">请确保 Android: ADB 已连接 ｜ iOS: iTunes + tidevice 已安装</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {devices.map((d) => (
                <button
                  key={d.device_id}
                  onClick={() => { setSelectedDevice(d); setSelectedApp('') }}
                  className={`flex items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50 ${
                    selectedDevice?.device_id === d.device_id ? 'border-primary ring-2 ring-primary/20' : ''
                  }`}
                >
                  <div className={`size-2.5 rounded-full ${d.status === 'online' ? 'bg-status-success-solid' : 'bg-status-danger-solid'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{d.device_name || d.device_id}</p>
                    <p className="text-xs text-muted-foreground">{d.device_model} · {d.os_version}</p>
                  </div>
                  <Badge tone="neutral" className="text-xs">{d.platform}</Badge>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Session form */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">采集配置</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {/* App selection */}
          <div>
            <Label className="text-sm">目标应用</Label>
            {selectedDevice ? (
              <Select value={selectedApp} onValueChange={setSelectedApp}>
                <SelectTrigger className="mt-1.5 h-9" aria-label="选择性能采集目标应用">
                  <SelectValue placeholder="选择或输入包名…" />
                </SelectTrigger>
                <SelectContent>
                  {(selectedDevice.installed_apps ?? []).map((app) => (
                    <SelectItem key={app} value={app}>{app}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <p className="mt-1.5 text-sm text-muted-foreground">请先选择设备</p>
            )}
            {/* Allow manual input even without installed_apps */}
            {selectedDevice && (
              <Input
                className="mt-1.5 h-9"
                placeholder="或手动输入包名 (如 com.cameltv.app)"
                value={selectedApp}
                onChange={(e) => setSelectedApp(e.target.value)}
              />
            )}
          </div>

          {/* Metrics */}
          <div>
            <Label className="text-sm">采集指标</Label>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {Object.entries(METRIC_LABELS).map(([key, label]) => (
                <label key={key} className="flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-sm cursor-pointer hover:bg-muted/50">
                  <Checkbox
                    checked={selectedMetrics.includes(key)}
                    onCheckedChange={(c) => {
                      if (c) setSelectedMetrics([...selectedMetrics, key])
                      else setSelectedMetrics(selectedMetrics.filter((m) => m !== key))
                    }}
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          {/* Duration */}
          <div>
            <Label className="text-sm">采集时长 (秒)</Label>
            <Select value={String(duration)} onValueChange={(v) => setDuration(Number(v))}>
              <SelectTrigger className="mt-1.5 h-9 w-40" aria-label="选择性能采集时长">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30 秒</SelectItem>
                <SelectItem value="60">60 秒</SelectItem>
                <SelectItem value="300">5 分钟</SelectItem>
                <SelectItem value="600">10 分钟</SelectItem>
                <SelectItem value="0">不限时长</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2 pt-2">
            <Button onClick={onCreateSession} disabled={!selectedDevice || !selectedApp}>
              创建会话
            </Button>
            {currentSession && currentSession.status === 'pending' && (
              <Button onClick={onStartMonitor} variant="primary" className="gap-1.5">
                <Play className="size-4" />开始采集
              </Button>
            )}
          </div>

          {currentSession && (
            <p className="text-xs text-muted-foreground">
              当前会话: {currentSession.session_id} ({STATUS_LABELS[currentSession.status] ?? currentSession.status})
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
