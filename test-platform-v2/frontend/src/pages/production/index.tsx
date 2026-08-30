import { useState } from 'react'
import { Link } from 'react-router'
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useAuthStore } from '@/stores/auth'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  analyzeGaps,
  fetchJourneys,
  type GapCandidate,
  type Journey,
  type JourneyDetail,
  type JourneyStep,
  type ObservationSession,
} from '@/api/production'
import { ProdReadOnlyBanner } from './components/ProdReadOnlyBanner'
import { ObservationSessionPanel } from './components/ObservationSessionPanel'
import { ObservedJourneyTimeline } from './components/ObservedJourneyTimeline'
import { RealStateDiscoveryTable } from './components/RealStateDiscoveryTable'
import { GapCandidatePanel } from './components/GapCandidatePanel'
import { ArrowRight, FileCheck, GitBranch, ShieldCheck, Layers } from '@/lib/icons'

/**
 * AITDE V3.6 Production Evidence hub — four sections behind a read-only banner.
 */
export default function ProductionEvidencePage() {
  const currentProjectId = useAuthStore((s) => s.currentProjectId)
  const [session, setSession] = useState<ObservationSession | null>(null)
  const [journeys, setJourneys] = useState<Journey[]>([])
  const [journeysLoading, setJourneysLoading] = useState(false)
  const [stepsByJourney, setStepsByJourney] = useState<Record<number, JourneyStep[]>>({})
  const [selectedJourneyId, setSelectedJourneyId] = useState<string>('')
  const [gaps, setGaps] = useState<GapCandidate[]>([])
  const [gapsLoading, setGapsLoading] = useState(false)

  // Load journeys for the current session (or all journeys when none selected).
  useAbortableEffect((signal) => {
    const sessionId = session?.id
    setJourneysLoading(true)
    setJourneys([])
    setSelectedJourneyId('')
    setGaps([])
    setStepsByJourney({})
    fetchJourneys(sessionId, signal)
      .then((rows) => {
        if (!signal.aborted) {
          setJourneys(rows)
          setSelectedJourneyId(rows[0] ? String(rows[0].id) : '')
          setGaps([])
          setStepsByJourney({})
        }
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setJourneysLoading(false)
      })
  }, [session?.id])

  // Analyze gaps for the selected journey (one request per selection).
  useAbortableEffect((signal) => {
    const journeyId = Number(selectedJourneyId)
    if (!Number.isFinite(journeyId) || journeyId <= 0) {
      setGaps([])
      return
    }
    if (!currentProjectId) return
    setGapsLoading(true)
    analyzeGaps(journeyId, { project_id: currentProjectId, journey_id: journeyId })
      .then((rows) => {
        if (!signal.aborted) setGaps(rows)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setGapsLoading(false)
      })
  }, [selectedJourneyId, currentProjectId])

  const handleJourneyDetail = (detail: JourneyDetail) => {
    setStepsByJourney((prev) => ({ ...prev, [detail.id]: detail.steps }))
  }

  return (
    <div className="space-y-4">
      <ProdReadOnlyBanner />
      <PageHeader title="生产证据" description="真实世界数据采集 · Journey 回放 · 模板与脱敏（V36-013/014）" />
      {currentProjectId == null && (
        <p className="text-sm text-muted-foreground">未选择项目，无法执行生产数据操作。</p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4" /> 一、观察会话
          </CardTitle>
          <CardDescription>启动 / 停止生产观察会话，采集真实世界数据。</CardDescription>
        </CardHeader>
        <CardContent>
          <ObservationSessionPanel
            projectId={currentProjectId}
            onChange={(next) => setSession(next)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="size-4" /> 二、真实状态发现
            <Badge tone="neutral">{journeys.length} Journeys</Badge>
          </CardTitle>
          <CardDescription>观察到的 Journey 及其步骤时间线、脱敏网络请求明细。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ObservedJourneyTimeline
            journeys={journeys}
            loading={journeysLoading}
            onDetail={handleJourneyDetail}
          />
          <RealStateDiscoveryTable journeys={journeys} loading={journeysLoading} stepsByJourney={stepsByJourney} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="size-4" /> 三、证据缺口
          </CardTitle>
          <CardDescription>选择 Journey 后运行缺口分析，识别需人工审批的候选。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Select value={selectedJourneyId} onValueChange={setSelectedJourneyId}>
              <SelectTrigger className="w-[280px]">
                <SelectValue placeholder="选择 Journey" />
              </SelectTrigger>
              <SelectContent>
                {journeys.map((j) => (
                  <SelectItem key={j.id} value={String(j.id)}>
                    {j.name || `Journey #${j.id}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <GapCandidatePanel candidates={gaps} loading={gapsLoading} />
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCheck className="size-4" /> 四、模板构建
            </CardTitle>
            <CardDescription>实体图谱 → 模板构建 / 校验 / 物化。</CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/production/templates"
              className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-input bg-background px-2.5 text-[0.8rem] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              打开模板中心 <ArrowRight className="size-3.5" />
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-4" /> 四、脱敏配置
            </CardTitle>
            <CardDescription>创建 masking profile 与规则。</CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/admin/masking"
              className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-input bg-background px-2.5 text-[0.8rem] font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              打开脱敏配置 <ArrowRight className="size-3.5" />
            </Link>
          </CardContent>
        </Card>
      </div>

      {journeysLoading && <Skeleton className="h-24 w-full" />}
    </div>
  )
}
