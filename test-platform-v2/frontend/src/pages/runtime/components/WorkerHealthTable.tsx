import { Badge, Button } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { WORKER_STATUS_LABELS, type WorkerNode } from '@/api/runtime'
import { AlertCircle, RefreshCw } from '@/lib/icons'
import { NetworkZoneBadge } from './NetworkZoneBadge'
import { WorkerCapabilityTags } from './WorkerCapabilityTags'

interface Props {
  workers: WorkerNode[]
  loading: boolean
  onDrain?: (id: number) => void
  onDisable?: (id: number) => void
  onRefresh?: () => void
}

export function WorkerHealthTable({ workers, loading, onDrain, onDisable, onRefresh }: Props) {
  if (loading) return <p className="text-sm text-muted-foreground">加载中…</p>
  if (!workers.length) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 border-y border-border py-4">
        <div>
          <p className="text-sm font-medium">尚未发现 Worker</p>
          <p className="mt-1 text-sm text-muted-hc">
            请管理员按部署 Runbook 启动执行节点后重新检查。
          </p>
        </div>
        {onRefresh && (
          <Button variant="secondary" className="min-h-11" onClick={onRefresh}>
            <RefreshCw className="size-4" aria-hidden="true" />
            重新检查
          </Button>
        )}
      </div>
    )
  }
  const hasOfflineWorker = workers.some((worker) => worker.status === 'OFFLINE')
  return (
    <div className="space-y-3">
      {hasOfflineWorker && (
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-y border-border py-3"
          role="status"
        >
          <div className="flex min-w-0 items-start gap-2">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-status-warning" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium">Worker 已停止心跳</p>
              <p className="mt-1 text-sm text-muted-hc">
                请管理员检查 Worker 进程、Control Plane 地址和网络连接；恢复后会自动变为在线。
              </p>
            </div>
          </div>
          {onRefresh && (
            <Button variant="secondary" className="min-h-11" onClick={onRefresh}>
              <RefreshCw className="size-4" aria-hidden="true" />
              重新检查
            </Button>
          )}
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>名称</TableHead>
            <TableHead>分区</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>能力</TableHead>
            <TableHead>版本</TableHead>
            <TableHead>心跳</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {workers.map((w) => {
            const status = WORKER_STATUS_LABELS[w.status]
            return (
              <TableRow key={w.id}>
                <TableCell className="font-medium">{w.name}</TableCell>
                <TableCell><NetworkZoneBadge zone={w.network_zone} /></TableCell>
                <TableCell>
                  <Badge tone="neutral" className={status?.color}>{status?.label ?? w.status}</Badge>
                </TableCell>
                <TableCell><WorkerCapabilityTags capabilities={w.capabilities} /></TableCell>
                <TableCell className="text-muted-foreground">{w.version || '-'}</TableCell>
                <TableCell className="text-muted-foreground">{w.last_heartbeat_at ? new Date(w.last_heartbeat_at).toLocaleString() : '-'}</TableCell>
                <TableCell className="text-right">
                  {w.status === 'ONLINE' ? (
                    <div className="flex justify-end gap-1">
                      {onDrain && <Button size="sm" variant="secondary" onClick={() => onDrain(w.id)}>排空</Button>}
                      {onDisable && <Button size="sm" variant="ghost" onClick={() => onDisable(w.id)}>禁用</Button>}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-hc">
                      {w.status === 'OFFLINE' ? '等待恢复心跳' : '当前状态不可操作'}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
