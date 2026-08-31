import { useParams, Link } from 'react-router'
import { useState } from 'react'
import { Badge, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import PageHeader from '@/components/PageHeader'
import { CampaignProgress } from '@/components/trust/CampaignProgress'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchCampaign, type Campaign } from '@/api/continuous'

const CAMPAIGN_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  IMPACTED: { label: '影响范围', color: 'bg-status-info-muted text-status-info' },
  FULL: { label: '全量', color: 'bg-status-warning-muted text-status-warning' },
  SMOKE: { label: '冒烟', color: 'bg-status-info-muted text-status-info' },
  CUSTOM: { label: '自定义', color: 'bg-muted text-muted-foreground' },
}

/** V35-013 Campaign 详情 — 展示选中场景以及每个场景的 selection reason。 */
export default function CampaignDetailPage() {
  const { id } = useParams()
  const campaignId = Number(id)
  useDocumentTitle('Campaign 详情')
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useAbortableEffect((signal) => {
    if (!campaignId) return
    setLoading(true)
    fetchCampaign(campaignId, signal)
      .then((res) => setCampaign(res))
      .catch((err) => {
        if (err?.code === 'ERR_CANCELED') return
        setError('Campaign 不存在或无法加载')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [campaignId])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="space-y-4">
        <PageHeader title="Campaign 详情" description="无法加载" />
        <p className="text-sm text-muted-foreground">{error}</p>
        <Link to="/workbench" className="text-sm text-primary hover:underline">返回工作台</Link>
      </div>
    )
  }

  const type = CAMPAIGN_TYPE_LABELS[campaign.campaign_type]
  const scenarios = campaign.scenarios ?? []

  return (
    <div className="space-y-4">
      <PageHeader
        title="Campaign 详情"
        description={`固定某次 Build 的 Scenario 选择快照（V35-013）· ${campaign.name || `Campaign #${campaign.id}`}`}
      />
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            {campaign.name || `Campaign #${campaign.id}`}
            <Badge tone="neutral" className={type?.color}>{type?.label ?? campaign.campaign_type}</Badge>
            <Badge tone="neutral">{campaign.status}</Badge>
          </CardTitle>
          <div className="text-xs text-muted-foreground">
            Project #{campaign.project_id} · Mission #{campaign.mission_id} · 环境 #{campaign.environment_id}
            {campaign.build_observation_id && <> · Build #{campaign.build_observation_id}</>}
            {' · '}创建：{campaign.created_at ? new Date(campaign.created_at).toLocaleString() : '-'}
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            选中场景 {scenarios.length} 个（不可变快照，run start 后锁定）。
          </p>
          <CampaignProgress campaign={campaign} />
        </CardContent>
      </Card>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>场景</TableHead>
            <TableHead>场景版本</TableHead>
            <TableHead>必选</TableHead>
            <TableHead>选中原因</TableHead>
            <TableHead>Run</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {scenarios.map((s) => {
            const reason = s.selection_reason_json
            const reasonText = typeof reason === 'string' ? reason : JSON.stringify(reason ?? {})
            return (
              <TableRow key={s.id}>
                <TableCell className="font-mono">#{s.scenario_id}</TableCell>
                <TableCell className="font-mono">#{s.scenario_version_id}</TableCell>
                <TableCell>
                  <Badge tone="neutral" className={s.required === 'REQUIRED' ? 'bg-status-warning-muted text-status-warning' : 'bg-muted text-muted-foreground'}>
                    {s.required}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  <span className="font-mono text-xs">{reasonText}</span>
                </TableCell>
                <TableCell className="font-mono">
                  {s.run_id ? `#${s.run_id}` : '-'}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      <Link to="/workbench" className="text-sm text-primary hover:underline">返回工作台</Link>
    </div>
  )
}
