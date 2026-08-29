import { useState } from 'react'
import { useNavigate } from 'react-router'
import PageHeader from '@/components/PageHeader'
import {
  Badge,
  Button,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchMissions, type Mission } from '@/api/missions'
import {
  fetchMissionRuns,
  OUTCOME_LABELS,
  RUNTIME_STATUS_LABELS,
  type Run,
} from '@/api/executions'
import OutcomeBadge from '@/components/executions/OutcomeBadge'
import RuntimeStatusBadge from '@/components/executions/RuntimeStatusBadge'
import { FlaskConical } from '@/lib/icons'

const PAGE_SIZE = 20

export default function ExecutionCenterPage() {
  useDocumentTitle('执行中心')
  const navigate = useNavigate()

  const [missions, setMissions] = useState<Mission[]>([])
  const [missionsLoading, setMissionsLoading] = useState(true)
  const [missionId, setMissionId] = useState<number | null>(null)

  const [runs, setRuns] = useState<Run[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const [outcome, setOutcome] = useState('')
  const [runtimeStatus, setRuntimeStatus] = useState('')
  const [page, setPage] = useState(1)

  useAbortableEffect((signal) => {
    setMissionsLoading(true)
    fetchMissions({ page: 1, page_size: 100 }, signal)
      .then((res) => {
        setMissions(res.items)
        setMissionId((prev) => prev ?? res.items[0]?.id ?? null)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setMissionsLoading(false)
      })
  }, [])

  useAbortableEffect((signal) => {
    if (!missionId) {
      setRuns([])
      setTotal(0)
      setLoading(false)
      return
    }
    setLoading(true)
    fetchMissionRuns(
      missionId,
      { outcome, runtime_status: runtimeStatus, page, page_size: PAGE_SIZE },
      signal,
    )
      .then((res) => {
        setRuns(res.items)
        setTotal(res.total)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, outcome, runtimeStatus, page])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const missionName = (id: number) =>
    missions.find((m) => m.id === id)?.title ?? `#${id}`

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="执行中心"
        description="统一的执行记录与结果回放入口"
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={missionId ? String(missionId) : undefined}
          onValueChange={(v) => {
            setMissionId(Number(v))
            setPage(1)
          }}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="选择任务" />
          </SelectTrigger>
          <SelectContent>
            {missions.map((m) => (
              <SelectItem key={m.id} value={String(m.id)}>
                {m.mission_key} · {m.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={outcome} onValueChange={(v) => { setOutcome(v); setPage(1) }}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="全部结果" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部结果</SelectItem>
            {Object.entries(OUTCOME_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={runtimeStatus}
          onValueChange={(v) => { setRuntimeStatus(v); setPage(1) }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            {Object.entries(RUNTIME_STATUS_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>场景</TableHead>
                <TableHead>任务</TableHead>
                <TableHead>结果</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>证据</TableHead>
                <TableHead>触发</TableHead>
                <TableHead>创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="py-10 text-center text-muted-foreground"
                  >
                    <FlaskConical className="mx-auto mb-2 size-8 opacity-50" />
                    {missionId ? '暂无执行记录。' : '请先选择测试任务。'}
                  </TableCell>
                </TableRow>
              ) : (
                runs.map((r) => (
                  <TableRow
                    key={r.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/executions/${r.id}`)}
                  >
                    <TableCell className="font-mono text-xs">#{r.id}</TableCell>
                    <TableCell className="font-mono text-xs">#{r.scenario_id}</TableCell>
                    <TableCell>{missionName(r.mission_id)}</TableCell>
                    <TableCell>
                      <OutcomeBadge outcome={r.outcome} />
                    </TableCell>
                    <TableCell>
                      <RuntimeStatusBadge status={r.runtime_status} />
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{r.evidence_status}</Badge>
                    </TableCell>
                    <TableCell>{r.trigger_type}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {r.created_at ?? '—'}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">共 {total} 条</span>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            上一页
          </Button>
          <span>
            {page} / {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  )
}
