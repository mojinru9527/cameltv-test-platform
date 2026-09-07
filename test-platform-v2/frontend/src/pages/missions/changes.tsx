import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  CHANGE_KIND_LABELS,
  CHANGE_ENTITY_TYPE_LABELS,
  CHANGE_RISK_HINT_LABELS,
  CHANGE_SET_STATUS_LABELS,
  CHANGE_TYPE_LABELS,
  fetchMissionChangeSets,
  type ChangeSet,
} from '@/api/smartRegression'
import { RefreshCw } from '@/lib/icons'

export default function MissionChangesPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const navigate = useNavigate()
  useDocumentTitle('变化检测')
  const [changeSets, setChangeSets] = useState<ChangeSet[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadVersion, setReloadVersion] = useState(0)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionChangeSets(missionId, signal)
      .then(({ items }) => {
        setChangeSets(items)
        setSelectedId((current) => current || String(items[0]?.id ?? ''))
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '变化记录加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, reloadVersion])

  const changeSet = changeSets.find((item) => item.id === Number(selectedId)) ?? changeSets[0]

  if (loading && changeSets.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="变化检测"
      >
          <Button
            variant="ghost"
            size="icon"
            aria-label="刷新变化记录"
            title="刷新变化记录"
            onClick={() => setReloadVersion((value) => value + 1)}
          >
            <RefreshCw className="size-4" />
          </Button>
      </PageHeader>

      {changeSets.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Select value={String(changeSet?.id ?? '')} onValueChange={setSelectedId}>
            <SelectTrigger className="w-full sm:w-[320px]" aria-label="选择变化记录">
              <SelectValue placeholder="选择变化记录" />
            </SelectTrigger>
            <SelectContent>
              {changeSets.map((item) => (
                <SelectItem key={item.id} value={String(item.id)}>
                  #{item.id} · {CHANGE_TYPE_LABELS[item.change_type] ?? item.change_type} · {item.items.length} 项
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {changeSet && (
            <Button
              size="sm"
              onClick={() => navigate(`/missions/${missionId}/impact?changeSet=${changeSet.id}`)}
            >
              查看影响
            </Button>
          )}
        </div>
      )}

      {changeSet ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-base">
              变化记录 #{changeSet.id}
              <Badge tone="neutral">{CHANGE_TYPE_LABELS[changeSet.change_type] ?? changeSet.change_type}</Badge>
              <Badge tone="neutral">{CHANGE_SET_STATUS_LABELS[changeSet.status] ?? changeSet.status}</Badge>
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              <span className="font-mono">{changeSet.content_hash.slice(0, 16)}…</span>
              {' · '}{changeSet.created_at ? new Date(changeSet.created_at).toLocaleString() : '-'}
              {' · '}{changeSet.items.length} 项
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {changeSet.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">本次检测未发现变化。</p>
            ) : (
              changeSet.items.map((item) => (
                <div
                  key={item.id}
                  className="grid gap-1 border-b py-2 text-sm last:border-0 sm:grid-cols-[auto_minmax(9rem,1fr)_minmax(12rem,2fr)_auto] sm:items-center"
                >
                  <Badge tone="neutral">
                    {CHANGE_KIND_LABELS[item.change_kind] ?? item.change_kind}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {CHANGE_ENTITY_TYPE_LABELS[item.entity_type] ?? item.entity_type}
                  </span>
                  <span className="font-medium">{item.entity_key}</span>
                  {item.risk_hint !== 'NONE' && (
                    <Badge tone="warning">
                      {CHANGE_RISK_HINT_LABELS[item.risk_hint] ?? item.risk_hint}
                    </Badge>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          尚无持久化的变化检测结果。
        </div>
      )}
    </div>
  )
}
