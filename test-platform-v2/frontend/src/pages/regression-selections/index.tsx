import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { createCampaignFromSelection, fetchRegressionSelection, type RegressionSelection } from '@/api/smartRegression'

/** V37-013 Regression Selection preview: include / exclude / fallback + campaign. */
export default function RegressionSelectionDetailPage() {
  const { id } = useParams()
  const selectionId = Number(id)
  useDocumentTitle('回归选择')
  const [selection, setSelection] = useState<RegressionSelection | null>(null)
  const [loading, setLoading] = useState(true)
  const [campaignId, setCampaignId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)

  useAbortableEffect((signal) => {
    fetchRegressionSelection(selectionId, signal)
      .then((s) => setSelection(s))
      .catch(() => undefined)
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }, [selectionId])

  const onCampaign = async () => {
    setBusy(true)
    try {
      const r = await createCampaignFromSelection(selectionId, { name: 'Smart Regression', environment_id: 0 })
      setCampaignId(r.campaign_id)
    } finally {
      setBusy(false)
    }
  }

  if (loading && !selection) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (!selection) {
    return (
      <div className="space-y-4">
        <PageHeader title="回归选择" description="回归选择预览（V37-013）" />
        <p className="text-sm text-muted-foreground">选择不存在。</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title={`回归选择 #${selection.id}`} description="Include / Exclude / Fallback 预览（V37-013）" />
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral">{selection.selection_type}</Badge>
            <span className="text-sm font-normal text-muted-foreground">选中 {selection.selected.length} · 排除 {selection.excluded.length}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button size="sm" onClick={onCampaign} disabled={busy || selection.selected.length === 0}>
            {busy ? '固化中…' : '固化为 Campaign'}
          </Button>
          {campaignId && <Badge tone="success">Campaign #{campaignId} 已生成</Badge>}
          {selection.fallback_reason && (
            <div className="rounded-md border border-status-warning p-2 text-sm text-status-warning">
              触发 fallback（{selection.fallback_reason}）
            </div>
          )}

          <div>
            <div className="mb-1.5 text-sm font-medium">选中 Scenario</div>
            {selection.selected.length ? (
              <div className="space-y-1.5">
                {selection.selected.map((s) => (
                  <div key={s.scenario_id} className="flex flex-wrap items-center gap-2 rounded-md border p-2 text-sm">
                    <Badge tone="neutral">选中</Badge>
                    <span className="font-medium">Scenario #{s.scenario_id}</span>
                    <span className="text-xs text-muted-foreground">版本 #{s.scenario_version_id || '—'}</span>
                    <span className="max-w-[48ch] text-xs text-muted-foreground">{s.reason}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">无选中项。</p>
            )}
          </div>

          <div>
            <div className="mb-1.5 text-sm font-medium">排除 Scenario</div>
            {selection.excluded.length ? (
              <div className="space-y-1.5">
                {selection.excluded.map((s) => (
                  <div key={s.scenario_id} className="flex flex-wrap items-center gap-2 rounded-md border p-2 text-sm">
                    <Badge tone="neutral" className="bg-muted text-muted-foreground">排除</Badge>
                    <span className="font-medium">Scenario #{s.scenario_id}</span>
                    <span className="max-w-[48ch] text-xs text-muted-foreground">{s.reason}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">无排除项。</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
