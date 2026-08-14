import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'
import {
  Smartphone, History, BarChart3, Gauge,
} from '@/lib/icons'
import { Button } from '@/ui'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PageHeader from '@/components/PageHeader'
import { usePerfWebSocket } from '@/hooks/usePerfWebSocket'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  fetchDevices, fetchSessions, fetchSession, createSession,
  deleteSession, startSession, stopSession,
  fetchReport, compareSessions,
  type PerfDevice, type PerfSession, type PerfSessionCreate,
  type PerfReport, type CompareResponse,
} from '@/api/perftest'
import { isCollectorUnavailable } from './components/perfShared'
import CollectorUnavailableBanner from './components/CollectorUnavailableBanner'
import DeviceCollectionPanel from './components/DeviceCollectionPanel'
import MonitorPanel from './components/MonitorPanel'
import SessionHistoryPanel from './components/SessionHistoryPanel'
import ReportPanel from './components/ReportPanel'

// ── Page ──

export default function PerfTestPage() {
  useDocumentTitle('性能测试')
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') || 'device'
  const [activeTab, setActiveTab] = useState(tabParam)
  const [loading, setLoading] = useState(false)

  // Device state
  const [devices, setDevices] = useState<PerfDevice[]>([])
  const [collectorUnavailable, setCollectorUnavailable] = useState(false)
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

  // mounted guard — prevents state updates after unmount (engineering-standards §4.1)
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  // ── Device ──

  const loadDevices = useCallback(async (signal?: AbortSignal) => {
    if (!mountedRef.current) return
    setLoading(true)
    setCollectorUnavailable(false)
    try {
      const list = await fetchDevices(signal)
      if (!mountedRef.current) return
      setDevices(list)
    } catch (error) {
      if (signal?.aborted) return
      if (!mountedRef.current) return
      setDevices([])
      setSelectedDevice(null)
      setSelectedApp('')
      if (isCollectorUnavailable(error)) {
        setCollectorUnavailable(true)
      } else {
        toast.error('获取设备列表失败')
      }
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [])

  useAbortableEffect((signal) => { void loadDevices(signal) }, [loadDevices])

  // ── Session ──

  const loadSessions = useCallback(async (signal?: AbortSignal) => {
    if (!mountedRef.current) return
    try {
      const data = await fetchSessions({ page: 1, page_size: 50 }, signal)
      if (!mountedRef.current) return
      setSessions(data.items)
      setTotalSessions(data.total)
    } catch {
      if (signal?.aborted) return
      // ignore
    }
  }, [])

  useAbortableEffect((signal) => { void loadSessions(signal) }, [loadSessions])

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

      {collectorUnavailable && (
        <CollectorUnavailableBanner
          loading={loading}
          onRetry={() => { void loadDevices() }}
        />
      )}

      <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setSearchParams({ tab: v }) }}>
        <TabsList className="grid w-full grid-cols-2 gap-1 group-data-[orientation=horizontal]/tabs:h-auto sm:w-auto sm:grid-cols-4">
          <TabsTrigger value="device" className="min-h-11 gap-1.5"><Smartphone className="size-4" />设备与采集</TabsTrigger>
          <TabsTrigger value="monitor" className="min-h-11 gap-1.5"><Gauge className="size-4" />实时监控</TabsTrigger>
          <TabsTrigger value="history" className="min-h-11 gap-1.5"><History className="size-4" />历史记录</TabsTrigger>
          <TabsTrigger value="report" className="min-h-11 gap-1.5"><BarChart3 className="size-4" />报告与对比</TabsTrigger>
        </TabsList>

        {/* ── Tab 1: Device & Collection ── */}
        <TabsContent value="device">
          {activeTab === 'device' && (
            <DeviceCollectionPanel
              devices={devices}
              loading={loading}
              collectorUnavailable={collectorUnavailable}
              selectedDevice={selectedDevice}
              setSelectedDevice={setSelectedDevice}
              selectedApp={selectedApp}
              setSelectedApp={setSelectedApp}
              selectedMetrics={selectedMetrics}
              setSelectedMetrics={setSelectedMetrics}
              duration={duration}
              setDuration={setDuration}
              currentSession={currentSession}
              onCreateSession={handleCreateSession}
              onStartMonitor={handleStartMonitor}
              onRefreshDevices={() => { void loadDevices() }}
            />
          )}
        </TabsContent>

        {/* ── Tab 2: Monitor ── */}
        <TabsContent value="monitor">
          {activeTab === 'monitor' && (
            <MonitorPanel
              monitoring={monitoring}
              wsMode={wsMode}
              reconnectCount={reconnectCount}
              snapshots={snapshots}
              latestValues={latestValues}
              selectedMetrics={selectedMetrics}
              currentSession={currentSession}
              onStartMonitor={handleStartMonitor}
              onStopMonitor={handleStopMonitor}
            />
          )}
        </TabsContent>

        {/* ── Tab 3: History ── */}
        <TabsContent value="history">
          {activeTab === 'history' && (
            <SessionHistoryPanel
              sessions={sessions}
              totalSessions={totalSessions}
              compareA={compareA}
              compareB={compareB}
              setCompareA={setCompareA}
              setCompareB={setCompareB}
              onLoadReport={loadReport}
              onCompare={handleCompare}
              onRefresh={() => { void loadSessions() }}
            />
          )}
        </TabsContent>

        {/* ── Tab 4: Report & Compare ── */}
        <TabsContent value="report">
          {activeTab === 'report' && (
            <ReportPanel
              report={report}
              compareResult={compareResult}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
