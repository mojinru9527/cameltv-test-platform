import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { CHANGE_KIND_LABELS, detectChanges, fetchChangeSet, type ChangeSet } from '@/api/smartRegression'

const CHANGE_TYPES = ['PRD', 'OPENAPI', 'DB_SCHEMA', 'UI_DISCOVERY', 'ENVIRONMENT', 'HISTORICAL_RISK']

/** V37-003..007 ChangeSet viewer: detect a change and inspect the normalized items. */
export default function MissionChangesPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('变化检测')
  const [changeType, setChangeType] = useState('PRD')
  const [changeSet, setChangeSet] = useState<ChangeSet | null>(null)
  const [loading, setLoading] = useState(false)
  const [detecting, setDetecting] = useState(false)

  const load = (signal?: AbortSignal) => {
    if (!missionId) return
    setLoading(true)
    fetchChangeSet(0, signal)
      .catch(() => undefined)
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }

  useAbortableEffect((signal) => {
    load(signal)
  }, [missionId])

  const onDetect = async (baseline: Record<string, unknown>, current: Record<string, unknown>) => {
    setDetecting(true)
    try {
      const cs = await detectChanges(missionId, { change_type: changeType, baseline, current })
      setChangeSet(cs)
    } finally {
      setDetecting(false)
    }
  }

  if (loading && !changeSet) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title="变化检测" description="ChangeSet 检测与归一化差异查看（V37-003..007）" />
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            发起检测
            <Select value={changeType} onValueChange={setChangeType}>
              <SelectTrigger className="w-[190px]">
                <SelectValue placeholder="变更类型" />
              </SelectTrigger>
              <SelectContent>
                {CHANGE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2 text-sm">
            <Button size="sm" disabled={detecting} onClick={() => void onDetect({ frag1: { content_hash: 'a' } }, { frag1: { content_hash: 'c' }, frag2: { content_hash: 'd' } })}>
              {detecting ? '检测中…' : '示例 PRD Diff'}
            </Button>
            <Button size="sm" variant="secondary" disabled={detecting} onClick={() => void onDetect({}, { signals: [{ scenario_id: 1, risk_hint: 'LAST_BUSINESS_FAIL', reason: 'run 9 fail' }] })}>
              {detecting ? '检测中…' : '示例历史风险信号'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            生产环境由 CI/Trigger 自动推送 baseline/current 快照；此处用于人工快速观测。
          </p>
        </CardContent>
      </Card>

      {changeSet ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              ChangeSet #{changeSet.id}
              <Badge tone="neutral">{changeSet.change_type}</Badge>
              <Badge tone="neutral">{changeSet.status}</Badge>
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              hash <span className="font-mono">{changeSet.content_hash.slice(0, 16)}…</span> · 创建 {changeSet.created_at ? new Date(changeSet.created_at).toLocaleString() : '-'} · {changeSet.items.length} 项
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {changeSet.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">无变化项。</p>
            ) : (
              changeSet.items.map((it) => (
                <div key={it.id} className="flex flex-wrap items-center gap-2 border-b py-1.5 text-sm last:border-0">
                  <Badge tone="neutral">{CHANGE_KIND_LABELS[it.change_kind] ?? it.change_kind}</Badge>
                  <span className="font-mono text-xs text-muted-foreground">{it.entity_type}</span>
                  <span className="font-medium">{it.entity_key}</span>
                  {it.risk_hint !== 'NONE' && <Badge tone="warning">{it.risk_hint}</Badge>}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      ) : (
        <p className="text-sm text-muted-foreground">尚未发起检测。</p>
      )}
    </div>
  )
}
