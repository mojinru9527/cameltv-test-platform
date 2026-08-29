import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import { Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchScenario } from '@/api/scenarios'
import { HybridRunLauncher } from '@/components/browser/HybridRunLauncher'

/** @/missions/:missionId/scenarios/:scenarioId/hybrid-run */
export default function HybridRunPage() {
  const { scenarioId } = useParams()
  const scenarioIdNum = Number(scenarioId)
  useDocumentTitle('Hybrid Run')

  const [scenarioVersionId, setScenarioVersionId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useAbortableEffect((signal) => {
    if (!scenarioIdNum) return
    fetchScenario(scenarioIdNum)
      .then((detail) => setScenarioVersionId(detail.scenario_version_id))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载场景失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [scenarioIdNum])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <HybridRunLauncher scenarioId={scenarioIdNum} scenarioVersionId={scenarioVersionId} />
    </div>
  )
}
