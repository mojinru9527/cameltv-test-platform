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
import { NetworkZoneBadge } from './NetworkZoneBadge'
import { WorkerCapabilityTags } from './WorkerCapabilityTags'

interface Props {
  workers: WorkerNode[]
  loading: boolean
  onDrain?: (id: number) => void
  onDisable?: (id: number) => void
}

export function WorkerHealthTable({ workers, loading, onDrain, onDisable }: Props) {
  if (loading) return <p className="text-sm text-muted-foreground">加载中…</p>
  if (!workers.length) return <p className="text-sm text-muted-foreground">暂无 Worker</p>
  return (
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
              <TableCell><WorkerCapabilityTags capabilities={w.capabilities ?? []} /></TableCell>
              <TableCell className="text-muted-foreground">{w.version || '-'}</TableCell>
              <TableCell className="text-muted-foreground">{w.last_heartbeat_at ? new Date(w.last_heartbeat_at).toLocaleString() : '-'}</TableCell>
              <TableCell className="text-right">
                {w.status === 'ONLINE' && (
                  <div className="flex justify-end gap-1">
                    {onDrain && <Button size="sm" variant="secondary" onClick={() => onDrain(w.id)}>排空</Button>}
                    {onDisable && <Button size="sm" variant="ghost" onClick={() => onDisable(w.id)}>禁用</Button>}
                  </div>
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
