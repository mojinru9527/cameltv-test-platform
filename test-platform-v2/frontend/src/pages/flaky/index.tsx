import { useState } from 'react'
import { Badge, Button, Input, Skeleton } from '@/ui'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  listFlaky,
  type FlakyCluster,
} from '@/api/aiClosedLoop'

const CLASSIFICATION_LABELS: Record<string, { label: string; color: string }> = {
  FLAKY: { label: 'Flaky', color: 'bg-status-danger-muted text-status-danger' },
  FLAPPY: { label: 'Flappy', color: 'bg-status-warning-muted text-status-warning' },
  UNCLASSIFIED: { label: '未分类', color: 'bg-muted text-muted-foreground' },
  STABLE: { label: '稳定', color: 'bg-status-success-muted text-status-success' },
}

/** V38-006/007 Flaky Trend: clusters with traceable samples, BusinessFail excluded. */
export default function FlakyPage() {
  useDocumentTitle('Flaky 分析')
  const [adapterInput, setAdapterInput] = useState('')
  const [adapterId, setAdapterId] = useState<number | null>(null)
  const [clusters, setClusters] = useState<FlakyCluster[]>([])
  const [loading, setLoading] = useState(false)

  useAbortableEffect((signal) => {
    if (adapterId === null) return
    setLoading(true)
    listFlaky(adapterId, signal)
      .then((rows) => setClusters(rows))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载 Flaky 失败')
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }, [adapterId])

  const doLoad = () => {
    const sid = Number(adapterInput)
    if (!sid) {
      toast.error('请输入 scenario_adapter_id')
      return
    }
    setAdapterId(sid)
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Flaky 分析" description="Flaky 聚类与趋势；仅 AUTOMATION/ENV 波动纳入，BusinessFail 永不标 Flaky（V38-006/007）" />
      <div className="flex flex-wrap items-end gap-2">
        <div className="w-48 space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">scenario_adapter_id</label>
          <Input
            type="number"
            value={adapterInput}
            onChange={(e) => setAdapterInput(e.target.value)}
            placeholder="场景适配器 ID"
          />
        </div>
        <Button onClick={doLoad} disabled={loading}>
          {loading ? '加载中…' : '加载聚类'}
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : clusters.length === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          {adapterId === null ? '输入 scenario_adapter_id 以加载 Flaky 聚类' : '暂无可追溯样本'}
        </div>
      ) : (
        <div className="space-y-2">
          {clusters.map((c) => {
            const meta = CLASSIFICATION_LABELS[c.classification]
            return (
              <div key={c.id} className="rounded-md border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral" className={meta?.color ?? ''}>{meta?.label ?? c.classification}</Badge>
                  <span className="font-mono text-sm">{c.cluster_key}</span>
                  <span className="text-xs text-muted-foreground">样本 {c.sample_size} · 失败率 {c.failure_rate.toFixed(2)}</span>
                  <span className="ml-auto text-xs text-muted-foreground">置信度 {(c.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
