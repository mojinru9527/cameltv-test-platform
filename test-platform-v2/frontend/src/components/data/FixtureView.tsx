import { useState } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Input, Skeleton } from '@/ui'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { FixtureStatusBadge } from './FixtureStatusBadge'
import { FixtureManifestViewer } from './FixtureManifestViewer'
import { LeaseIndicator } from './LeaseIndicator'
import { DbSnapshotDiff } from './DbSnapshotDiff'
import { CleanupStatus } from './CleanupStatus'
import {
  fetchFixture,
  fetchFixtureSnapshots,
  leaseFixture,
  releaseFixture,
  cleanupFixture,
  type Fixture,
  type FixtureLease,
  type FixtureSnapshot,
} from '@/api/fixtures'
import { KeyRound, RefreshCw, Trash2, Lock, FileDown } from '@/lib/icons'

type ActionId = 'lease' | 'release' | 'cleanup' | null

export interface FixtureViewProps {
  fixtureId: number
}

/** Full fixture detail: manifest, leases, snapshots diff + lifecycle actions. */
export function FixtureView({ fixtureId }: FixtureViewProps) {
  const [fixture, setFixture] = useState<Fixture | null>(null)
  const [snapshots, setSnapshots] = useState<FixtureSnapshot[]>([])
  const [lease, setLease] = useState<FixtureLease | null>(null)
  const [loading, setLoading] = useState(true)
  const [snapshotsLoading, setSnapshotsLoading] = useState(true)
  const [acting, setActing] = useState<ActionId>(null)
  const [reloadNonce, setReloadNonce] = useState(0)

  // ── Lease dialog state ──
  const [leaseOpen, setLeaseOpen] = useState(false)
  const [leaseRunId, setLeaseRunId] = useState('')
  const [leaseTtl, setLeaseTtl] = useState('')

  const reload = () => setReloadNonce((n) => n + 1)

  useAbortableEffect((signal) => {
    if (!fixtureId) return
    setLoading(true)
    fetchFixture(fixtureId, signal)
      .then(setFixture)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [fixtureId, reloadNonce])

  useAbortableEffect((signal) => {
    if (!fixtureId) return
    setSnapshotsLoading(true)
    fetchFixtureSnapshots(fixtureId, signal)
      .then(setSnapshots)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) setSnapshots([])
      })
      .finally(() => {
        if (!signal.aborted) setSnapshotsLoading(false)
      })
  }, [fixtureId, reloadNonce])

  const doLease = async () => {
    const runId = Number(leaseRunId)
    if (!runId) {
      toast.error('请输入 run_id')
      return
    }
    setActing('lease')
    try {
      const result = await leaseFixture(fixtureId, {
        run_id: runId,
        ttl_seconds: leaseTtl ? Number(leaseTtl) : undefined,
      })
      setLease(result)
      toast.success('已租用 fixture')
      setLeaseOpen(false)
      setLeaseRunId('')
      setLeaseTtl('')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '租用失败')
    } finally {
      setActing(null)
    }
  }

  const doRelease = async () => {
    if (!lease) {
      toast.error('当前无租约可释放')
      return
    }
    setActing('release')
    try {
      await releaseFixture(fixtureId, { lease_id: lease.id })
      setLease(null)
      toast.success('已释放 fixture')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '释放失败')
    } finally {
      setActing(null)
    }
  }

  const doCleanup = async () => {
    setActing('cleanup')
    try {
      const result = await cleanupFixture(fixtureId)
      toast.success(
        `清理 ${result.idempotent ? '(幂等) ' : ''}状态 ${result.status} · 第 ${result.attempt_no} 次`,
      )
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '清理失败')
    } finally {
      setActing(null)
    }
  }

  const doRefresh = () => {
    reload()
    toast.success('已刷新')
  }

  if (loading && !fixture) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (!fixture) {
    return (
      <div className="rounded-lg border bg-card py-16 text-center text-sm text-muted-foreground">
        未找到 fixture #{fixtureId}。
      </div>
    )
  }

  const leased = lease || fixture.status === 'LEASED'

  return (
    <div className="space-y-4">
      {/* Header card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            <span className="font-mono">Fixture #{fixture.id}</span>
            <FixtureStatusBadge status={fixture.status} />
          </CardTitle>
          <CardDescription>
            命名空间 <code className="font-mono text-xs">{fixture.namespace ?? '—'}</code> · 策略{' '}
            {fixture.strategy ?? '—'} · 环境 {fixture.environment_id ?? '—'} · 数据源{' '}
            {fixture.data_source_id ?? '—'}
          </CardDescription>
          <CardAction className="flex items-center gap-1">
            <LeaseIndicator lease={lease} leasedByStatus={fixture.status === 'LEASED'} />
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2">
            <Button className="min-h-11" disabled={Boolean(leased) || acting !== null} onClick={() => setLeaseOpen(true)}>
              <KeyRound className="size-4" /> 租用
            </Button>
            <Button variant="secondary" className="min-h-11" disabled={!lease || acting !== null} onClick={doRelease}>
              <Lock className="size-4" /> 释放
            </Button>
            <Button variant="secondary" className="min-h-11" disabled={acting !== null} onClick={doCleanup}>
              <Trash2 className="size-4" /> 清理
            </Button>
            <Button variant="ghost" className="min-h-11" onClick={doRefresh}>
              <RefreshCw className="size-4" /> 刷新
            </Button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">创建时间</p>
              <p className="font-mono text-xs">{fixture.created_at ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">过期时间</p>
              <p className="font-mono text-xs">{fixture.expires_at ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">数据源连接</p>
              <Badge variant="outline">{fixture.data_source_id ? `#${fixture.data_source_id}` : '—'}</Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">清理状态</p>
              <CleanupStatus cleanupStatus={fixture.cleanup_status} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Manifest */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileDown className="size-4" /> 实体清单 (manifest)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <FixtureManifestViewer manifest={fixture.manifest_json} entities={fixture.entities} />
        </CardContent>
      </Card>

      {/* Snapshots */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="size-4" /> 快照对比 (snapshots)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <DbSnapshotDiff snapshots={snapshots} />
          <div className="mt-6">
            <p className="mb-2 text-sm font-medium">快照列表</p>
            {snapshotsLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 2 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : snapshots.length === 0 ? (
              <p className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
                暂无双快照。
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>类型</TableHead>
                    <TableHead>实体</TableHead>
                    <TableHead>Run</TableHead>
                    <TableHead>哈希</TableHead>
                    <TableHead>创建时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snapshots.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell>
                        <Badge variant="outline">{s.snapshot_type}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{s.entity_id ?? 'global'}</TableCell>
                      <TableCell className="font-mono text-xs">{s.run_id ?? '—'}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {s.content_hash ?? '—'}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{s.created_at ?? '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Lease dialog */}
      <Dialog open={leaseOpen} onOpenChange={setLeaseOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>租用 fixture</DialogTitle>
            <DialogDescription>为 run_id 创建一条租约，TTL 可选（秒）。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="lease-run-id">run_id</label>
              <Input
                id="lease-run-id"
                inputMode="numeric"
                value={leaseRunId}
                onChange={(e) => setLeaseRunId(e.target.value)}
                placeholder="例如 1042"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="lease-ttl">ttl_seconds（可选）</label>
              <Input
                id="lease-ttl"
                inputMode="numeric"
                value={leaseTtl}
                onChange={(e) => setLeaseTtl(e.target.value)}
                placeholder="例如 3600"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setLeaseOpen(false)} disabled={acting !== null}>
              取消
            </Button>
            <Button onClick={doLease} disabled={acting !== null || !leaseRunId}>
              {acting === 'lease' ? '租用中…' : '租用'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
