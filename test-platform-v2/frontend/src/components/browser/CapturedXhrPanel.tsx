import { Badge } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { type BrowserSessionEvent } from '@/api/browserInteractions'

export interface CapturedXhrPanelProps {
  events: BrowserSessionEvent[]
}

interface XhrEntry {
  event: BrowserSessionEvent
  method: string | null
  path: string | null
  status: string | null
}

function isNetworkEvent(event: BrowserSessionEvent): boolean {
  const type = event.event_type.toLowerCase()
  return type.includes('network') || type.includes('xhr') || type.includes('request')
}

function toXhrEntry(event: BrowserSessionEvent): XhrEntry {
  const payload = event.payload_ref_json
  const method =
    typeof payload?.method === 'string'
      ? payload.method
      : typeof payload?.request_method === 'string'
        ? payload.request_method
        : null
  const path =
    typeof payload?.path === 'string'
      ? payload.path
      : typeof payload?.url === 'string'
        ? payload.url
        : null
  const status =
    typeof payload?.status === 'string'
      ? payload.status
      : typeof payload?.status === 'number'
        ? String(payload.status)
        : null
  return { event, method, path, status }
}

/**
 * Lists captured XHR / network requests observed during a browser session.
 * Method / path / status are extracted when present; the full payload remains
 * available below each row.
 */
export function CapturedXhrPanel({ events }: CapturedXhrPanelProps) {
  const entries = events.filter(isNetworkEvent).map(toXhrEntry).sort((a, b) => a.event.sequence - b.event.sequence)

  if (entries.length === 0) {
    return (
      <div className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
        暂无捕获的 XHR / 网络请求。
      </div>
    )
  }

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">#</TableHead>
            <TableHead>方法</TableHead>
            <TableHead>路径</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>类型</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(({ event, method, path, status }) => (
            <TableRow key={event.id}>
              <TableCell className="font-mono text-xs text-muted-foreground">{event.sequence}</TableCell>
              <TableCell>
                <Badge variant="outline" className="font-mono text-[11px]">{method ?? '—'}</Badge>
              </TableCell>
              <TableCell className="max-w-64 truncate font-mono text-xs" title={path ?? ''}>
                {path ?? '—'}
              </TableCell>
              <TableCell>
                {status ? (
                  <Badge tone={Number(status) >= 400 ? 'danger' : 'success'}>
                    {status}
                  </Badge>
                ) : (
                  '—'
                )}
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{event.event_type}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
