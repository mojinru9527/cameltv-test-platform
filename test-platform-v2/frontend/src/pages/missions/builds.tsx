import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchMissionBuilds,
  BUILD_STATUS_LABELS,
  type BuildObservation,
} from '@/api/continuous'

/** V35-011 Build Timeline — fingerprint-derived build trend (RED→GREEN). */
export default function MissionBuildsPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('Build 时间线')
  const [builds, setBuilds] = useState<BuildObservation[]>([])
  const [loading, setLoading] = useState(true)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionBuilds(missionId, signal)
      .then((res) => setBuilds(res.items))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Build 时间线"
        description="按环境指纹识别的新 Build，逐步形成验收状态（V35-011）"
      />
      {builds.length === 0 ? (
        <p className="text-sm text-muted-foreground">暂无 Build 记录。给环境采集指纹后生成。</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>指纹 Hash</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>变化</TableHead>
              <TableHead>检出时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {builds.map((b) => {
              const st = BUILD_STATUS_LABELS[b.status]
              return (
                <TableRow key={b.id}>
                  <TableCell className="font-mono">{b.id}</TableCell>
                  <TableCell className="font-mono text-xs">{b.fingerprint_id}</TableCell>
                  <TableCell>
                    <Badge tone="neutral" className={st?.color}>{st?.label ?? b.status}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {b.previous_fingerprint_id ? `变更自 #${b.previous_fingerprint_id}` : '首个 Build'}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {b.detected_at ? new Date(b.detected_at).toLocaleString() : '-'}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
