import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import {
  Smartphone, Play, Square, History, BarChart3, RefreshCw,
  Loader2, Wifi, WifiOff, AlertCircle, CheckCircle2, XCircle, Gauge,
} from '@/lib/icons'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import PageHeader from '@/components/PageHeader'
import DataTable from '@/components/DataTable'
import { usePerfWebSocket } from '@/hooks/usePerfWebSocket'
import {
  fetchDevices, fetchSessions, fetchSession, createSession,
  deleteSession, startSession, stopSession,
  fetchReport, compareSessions,
  type PerfDevice, type PerfSession, type PerfSessionCreate,
  type PerfReport, type MetricStatsItem, type CompareResponse,
} from '@/api/perftest'

// ── Constants ──

const METRIC_LABELS: Record<string, string> = {
  cpu: 'CPU', memory: '内存', fps: '帧率', jank: '卡顿(Jank)',
  startup: '启动耗时', anr: 'ANR/崩溃',
}
const METRIC_UNITS: Record<string, string> = {
  cpu: '%', memory: 'MB', fps: 'fps', jank: '次', startup: 'ms', anr: '次',
}
const STATUS_LABELS: Record<string, string> = {
  pending: '等待中', running: '采集中', completed: '已完成', failed: '失败', cancelled: '已取消',
}
const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending: 'secondary', running: 'default', completed: 'outline', failed: 'destructive', cancelled: 'secondary',
}

// ── Page ──

export default function PerfTestPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') || 'device'
  const [activeTab, setActiveTab] = useState(tabParam)
  const [loading, setLoading] = useState(false)

  // Device state
  const [devices, setDevices] = useState<PerfDevice[]>([])
  const [selectedDevice, setSelectedDevice] = useState<PerfDevice | null>(null)
  const [selectedApp, setSelectedApp] = useState('')
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['cpu', 'memory', 'fps', 'jank'])
  const [duration, setDuration] = useState(300)

  // Session state
  const [sessions, setSessions] = useState<PerfSession[]>([])
  const [totalSessions, setTotalSessions] = useState(0)
  const [currentSession, setCurrentSession] = useState<PerfSession | null>(null)

  // Monitor state
  const [monitoring, setMonitoring] = useState(false)
  const [snapshots, setSnapshots] = useState<{ ts: number; elapsed: number; values: Record<string, any> }[]>([])

  // Report state
  const [report, setReport] = useState<PerfReport | null>(null)
  const [compareA, setCompareA] = useState<number | null>(null)
  const [compareB, setCompareB] = useState<number | null>(null)
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null)

  // ── Device ──

  const loadDevices = useCallback(async () => {
    setLoading(true)
    try {
      const list = await fetchDevices()
      setDevices(list)
    } catch {
      toast.error('获取设备列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadDevices() }, [loadDevices])

  // ── Session ──

  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchSessions({ page: 1, page_size: 50 })
      setSessions(data.items)
      setTotalSessions(data.total)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => { loadSessions() }, [loadSessions])

  const handleCreateSession = async () => {
    if (!selectedDevice || !selectedApp || selectedMetrics.length === 0) {
      toast.error('请选择设备、应用和至少一项指标')
      return
    }
    try {
      const body: PerfSessionCreate = {
        device_id: selectedDevice.device_id,
        platform: selectedDevice.platform,
        pkg_name: selectedApp,
        device_name: selectedDevice.device_name,
        device_model: selectedDevice.device_model,
        metrics: selectedMetrics,
        duration,
      }
      const session = await createSession(body)
      toast.success(`会话 ${session.session_id} 已创建`)
      setCurrentSession(session)
      loadSessions()
    } catch {
      toast.error('创建会话失败')
    }
  }

  const handleStartMonitor = async () => {
    if (!currentSession) return
    try {
      await startSession(currentSession.id)
      setMonitoring(true)
      setSnapshots([])
      setActiveTab('monitor')
      setSearchParams({ tab: 'monitor' })
    } catch {
      toast.error('启动采集失败')
    }
  }

  const handleStopMonitor = async () => {
    if (!currentSession) return
    try {
      await stopSession(currentSession.id)
      setMonitoring(false)
      toast.success('采集已停止')
      loadSessions()
      setActiveTab('report')
      setSearchParams({ tab: 'report' })
    } catch {
      toast.error('停止采集失败')
    }
  }

  // ── WebSocket ──

  const handleSnapshot = useCallback((point: { timestamp: number; elapsed_s: number; values: Record<string, any> }) => {
    setSnapshots((prev) => [...prev.slice(-120), { ts: point.timestamp, elapsed: point.elapsed_s, values: point.values }])
  }, [])

  const handleEnd = useCallback((reason: string) => {
    setMonitoring(false)
    toast.info(`采集结束: ${reason}`)
    loadSessions()
  }, [loadSessions])

  const { mode: wsMode, reconnectCount } = usePerfWebSocket({
    sessionId: currentSession?.id ?? 0,
    enabled: monitoring,
    onSnapshot: handleSnapshot,
    onEnd: handleEnd,
  })

  // ── Report ──

  const loadReport = async (sessionId: number) => {
    try {
      const r = await fetchReport(sessionId)
      setReport(r)
      setActiveTab('report')
      setSearchParams({ tab: 'report' })
    } catch {
      toast.error('获取报告失败')
    }
  }

  const handleCompare = async () => {
    if (!compareA || !compareB) return
    try {
      const r = await compareSessions(compareA, compareB)
      setCompareResult(r)
    } catch {
      toast.error('对比失败')
    }
  }

  // ── Latest metric values for display ──

  const latestValues = snapshots.length > 0 ? snapshots[snapshots.length - 1].values : null

  return (
    <div className="space-y-4">
      <PageHeader title="性能测试" description="客户端性能采集（Android / iOS）——对标 PerfDog 数据口径，基于 SoloX 引擎" />

      <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setSearchParams({ tab: v }) }}>
        <TabsList>
          <TabsTrigger value="device" className="gap-1.5"><Smartphone className="size-4" />设备与采集</TabsTrigger>
          <TabsTrigger value="monitor" className="gap-1.5"><Gauge className="size-4" />实时监控</TabsTrigger>
          <TabsTrigger value="history" className="gap-1.5"><History className="size-4" />历史记录</TabsTrigger>
          <TabsTrigger value="report" className="gap-1.5"><BarChart3 className="size-4" />报告与对比</TabsTrigger>
        </TabsList>

        {/* ── Tab 1: Device & Collection ── */}
        <TabsContent value="device">
          {activeTab === 'device' && (
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Device list */}
              <Card>
                <CardHeader className="pb-2 flex-row items-center justify-between">
                  <CardTitle className="text-base">已连接设备</CardTitle>
                  <Button variant="ghost" size="icon" onClick={loadDevices} disabled={loading}>
                    <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
                  </Button>
                </CardHeader>
                <CardContent>
                  {loading && devices.length === 0 ? (
                    <div className="grid min-h-[120px] place-items-center"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
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
                          <div className={`size-2.5 rounded-full ${d.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{d.device_name || d.device_id}</p>
                            <p className="text-xs text-muted-foreground">{d.device_model} · {d.os_version}</p>
                          </div>
                          <Badge variant="outline" className="text-xs">{d.platform}</Badge>
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
                        <SelectTrigger className="mt-1.5 h-9">
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
                      <SelectTrigger className="mt-1.5 h-9 w-40">
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
                    <Button onClick={handleCreateSession} disabled={!selectedDevice || !selectedApp}>
                      创建会话
                    </Button>
                    {currentSession && currentSession.status === 'pending' && (
                      <Button onClick={handleStartMonitor} variant="default" className="gap-1.5">
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
          )}
        </TabsContent>

        {/* ── Tab 2: Monitor ── */}
        <TabsContent value="monitor">
          {activeTab === 'monitor' && (
            <div className="space-y-4">
              {/* Status bar */}
              <Card>
                <CardContent className="flex items-center gap-4 py-3">
                  <div className="flex items-center gap-2">
                    {wsMode === 'websocket' ? <Wifi className="size-4 text-emerald-500" /> : wsMode === 'polling' ? <WifiOff className="size-4 text-amber-500" /> : <Loader2 className="size-4 animate-spin" />}
                    <span className="text-sm">{wsMode === 'websocket' ? 'WebSocket 实时' : wsMode === 'polling' ? 'HTTP 轮询(降级)' : '连接中…'}</span>
                    {reconnectCount > 0 && <Badge variant="outline" className="text-xs">重连 {reconnectCount}/3</Badge>}
                  </div>
                  <div className="ml-auto flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      采样: {snapshots.length} 次
                      {snapshots.length > 0 && ` · ${snapshots[snapshots.length - 1].elapsed.toFixed(0)}s`}
                    </span>
                    {monitoring ? (
                      <Button onClick={handleStopMonitor} variant="destructive" size="sm" className="gap-1.5">
                        <Square className="size-3" />停止采集
                      </Button>
                    ) : (
                      currentSession && currentSession.status === 'pending' && (
                        <Button onClick={handleStartMonitor} size="sm" className="gap-1.5">
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
          )}
        </TabsContent>

        {/* ── Tab 3: History ── */}
        <TabsContent value="history">
          {activeTab === 'history' && (
            <Card>
              <CardHeader className="pb-2 flex-row items-center justify-between">
                <CardTitle className="text-base">采集记录 ({totalSessions})</CardTitle>
                <Button variant="ghost" size="icon" onClick={loadSessions}><RefreshCw className="size-4" /></Button>
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
                            <td className="py-2 pr-4 max-w-[120px] truncate">{s.device_name}</td>
                            <td className="py-2 pr-4 font-mono text-xs max-w-[150px] truncate">{s.pkg_name}</td>
                            <td className="py-2 pr-4">{s.actual_duration_s || s.duration}s</td>
                            <td className="py-2 pr-4">
                              <Badge variant={STATUS_VARIANTS[s.status] ?? 'secondary'} className="text-xs">
                                {STATUS_LABELS[s.status] ?? s.status}
                              </Badge>
                            </td>
                            <td className="py-2 pr-4 text-xs text-muted-foreground">
                              {s.created_at ? new Date(s.created_at).toLocaleString() : ''}
                            </td>
                            <td className="py-2">
                              <div className="flex gap-1">
                                <Button variant="ghost" size="sm" onClick={() => loadReport(s.id)} disabled={s.status !== 'completed'}>
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
                    <Button size="sm" onClick={handleCompare}>执行对比</Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── Tab 4: Report & Compare ── */}
        <TabsContent value="report">
          {activeTab === 'report' && (
            <div className="space-y-4">
              {/* Report */}
              {report && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">
                      采集报告: {report.session.session_id}
                      <Badge variant="outline" className="ml-2 text-xs">
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
                              <AlertCircle className="size-4 text-amber-500 shrink-0" />
                              <span className="text-xs text-muted-foreground font-mono">{new Date(a.timestamp * 1000).toLocaleTimeString()}</span>
                              <Badge variant="outline" className="text-xs">{a.event_type}</Badge>
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
                        <Card key={d.metric_type} className={`p-3 ${d.significant ? (d.direction === 'degraded' ? 'border-red-500/30 bg-red-50/30' : 'border-emerald-500/30 bg-emerald-50/30') : ''}`}>
                          <p className="text-xs text-muted-foreground">{METRIC_LABELS[d.metric_type] ?? d.metric_type}</p>
                          <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-lg font-bold tabular-nums">{d.session_a_mean}</span>
                            <span className="text-xs text-muted-foreground">vs</span>
                            <span className="text-sm tabular-nums">{d.session_b_mean}</span>
                          </div>
                          <p className={`text-xs mt-0.5 ${
                            d.direction === 'degraded' ? 'text-red-600' :
                            d.direction === 'improved' ? 'text-emerald-600' :
                            'text-muted-foreground'
                          }`}>
                            {d.delta_absolute > 0 ? '+' : ''}{d.delta_absolute} ({d.delta_percent > 0 ? '+' : ''}{d.delta_percent}%)
                            {d.significant && (d.direction === 'degraded' ? ' ⚠️ 恶化' : d.direction === 'improved' ? ' ✅ 改善' : '')}
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
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ── Trend chart ──

const CHART_COLORS: Record<string, string> = {
  fps: '#10b981',    // emerald-500
  cpu: '#3b82f6',    // blue-500
  memory: '#f59e0b', // amber-500
  jank: '#ef4444',   // red-500
}

function PerfTrendChart({
  snapshots,
  selectedMetrics,
}: {
  snapshots: { ts: number; elapsed: number; values: Record<string, any> }[]
  selectedMetrics: string[]
}) {
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
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                  <XAxis
                    dataKey="elapsed"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${v}s`}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    yAxisId="fps"
                    domain={[0, 'auto']}
                    tick={{ fontSize: 11 }}
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
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                  <XAxis
                    dataKey="elapsed"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${v}s`}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 11 }}
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
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                  <XAxis
                    dataKey="elapsed"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${v}s`}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    domain={[0, 'auto']}
                    tick={{ fontSize: 11 }}
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ── Metric stat card ──

function MetricStatCard({ stat }: { stat: MetricStatsItem }) {
  const label = METRIC_LABELS[stat.metric_type] ?? stat.metric_type
  const unit = stat.unit || METRIC_UNITS[stat.metric_type] || ''
  return (
    <div className={`rounded-lg border p-3 ${
      stat.passed ? 'border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/10' : 'border-red-500/30 bg-red-50/30 dark:bg-red-950/10'
    }`}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-xs font-medium">{label}</span>
        {stat.passed ? <CheckCircle2 className="size-3 text-emerald-500" /> : <XCircle className="size-3 text-red-500" />}
      </div>
      <p className="text-2xl font-bold tabular-nums">
        {stat.mean}
        <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
      <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
        <span>中位: {stat.median}</span>
        <span>P95: {stat.p95}</span>
        <span>最小: {stat.min_val}</span>
        <span>最大: {stat.max_val}</span>
        <span className="col-span-2">样本: {stat.samples} · SD: {stat.stddev}</span>
      </div>
    </div>
  )
}
